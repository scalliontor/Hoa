import com.vp.plugin.*;
import com.vp.plugin.diagram.IDiagramUIModel;
import java.awt.*;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;
import java.util.*;
import java.util.List;
import javax.swing.*;

/**
 * Screenshots of the Visual Paradigm window, for the diagram types the Community Edition cannot draw (BPMN,
 * DFD, ArchiMate), and of VP's own Generate Database wizard: the essay shows them as screenshots of the trial
 * edition rather than as watermarked exports. Active only when shots.request exists next to this plugin:
 *   line 1      output folder (receives shots.log and the PNG files)
 *   xml=...     diagrams to build, in the format of vp/diagrams.xml (TieuLuanBuilder builds them in the window;
 *               with project="" the project stays unsaved)
 *   name|file   one diagram per line
 *   ddl=...     optional: the builder also writes VP's DDL there and saves the SQLite database setting
 *   repo=...    optional: the repository, whose demo/lib holds the SQLite driver named in that setting
 *   dbsetup     optional: SQLite becomes the project's default database, with VP's own name for its driver
 *   steps=a>b>...|file   optional: after the diagrams, operate VP's window step by step and paint it, with any
 *               dialog, into file; the fields of every dialog are listed in shots.log. A step is
 *                 Label           click the button, ribbon tab or menu item with that label (?Label: if present)
 *                 popup:Label     open the dropdown of the ribbon button with that label
 *                 path=dir        type dir into the output folder of the open dialog
 *                 unless:Label@x,y  click the point x,y of the window (negative: from the right or bottom)
 *                                 unless a control with that label is already showing
 *                 shot:file       paint the window and its dialogs into file
 * For each diagram the plugin opens it, zooms it to the window and paints the window (with its title, e.g.
 * "... Visual Paradigm Enterprise (Evaluation Copy)") into a PNG at 2x; only VP's own window is painted, never
 * the rest of the screen. VP then quits without saving.
 */
public final class TieuLuanShots implements VPPlugin {
    private File out;

    @Override public void loaded(VPPluginInfo info) {
        File request = new File(info.getPluginDir(), "shots.request");
        if (!request.isFile()) return;
        Thread worker = new Thread(() -> run(request), "tieuluan-shots");
        worker.setDaemon(true);
        worker.start();
    }

    @Override public void unloaded() { }

    private void log(String line) {
        try {
            Files.write(new File(out, "shots.log").toPath(), (line + "\n").getBytes(StandardCharsets.UTF_8),
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (Exception ignored) { }
    }

    private static void edt(Runnable r) throws Exception { SwingUtilities.invokeAndWait(r); }

    private void run(File request) {
        try {
            List<String> lines = Files.readAllLines(request.toPath(), StandardCharsets.UTF_8);
            out = new File(lines.get(0).trim());
            out.mkdirs();
            Map<String, String> wanted = new LinkedHashMap<>();
            String xml = null, ddl = null, steps = null, stepsFile = null;
            boolean dbsetup = false;
            for (String l : lines.subList(1, lines.size())) {
                if (l.startsWith("xml=")) xml = l.substring(4).trim();
                else if (l.startsWith("ddl=")) ddl = l.substring(4).trim();
                else if (l.startsWith("repo=")) System.setProperty("tieuluan.repo", l.substring(5).trim());
                else if (l.trim().equals("dbsetup")) dbsetup = true;
                else if (l.startsWith("steps=")) {
                    String[] p = l.substring(6).split("\\|", 2);
                    steps = p[0].trim();
                    stepsFile = p.length > 1 ? p[1].trim() : "steps.png";
                }
                else if (l.contains("|")) {
                    String[] p = l.split("\\|", 2);
                    wanted.put(p[0].trim(), p[1].trim());
                }
            }
            log("start " + wanted.size());
            ViewManager vm = ApplicationManager.instance().getViewManager();
            Component frame = null;
            for (int i = 0; i < 120 && (frame == null || !frame.isShowing()); i++) {
                Thread.sleep(1000);
                try { frame = vm.getRootFrame(); } catch (Exception ignored) { }
            }
            Thread.sleep(6000);
            final ProjectManager pm = ApplicationManager.instance().getProjectManager();
            // Build the diagrams in the open (untitled) project with the essay's own builder.
            System.setProperty("tieuluan.root", out.getAbsolutePath());
            System.setProperty("tieuluan.xml", xml);
            System.setProperty("tieuluan.out", new File(out, "exports").getAbsolutePath());
            if (ddl != null) System.setProperty("tieuluan.ddl", ddl);
            edt(() -> new TieuLuanBuilder().invoke(new String[0]));
            log("built");
            Map<String, IDiagramUIModel> found = new HashMap<>();
            for (int i = 0; i < 120 && found.size() < wanted.size(); i++) {
                Thread.sleep(1000);
                for (IDiagramUIModel d : pm.getProject().toDiagramArray())
                    if (wanted.containsKey(d.getName())) found.put(d.getName(), d);
            }
            log("project " + pm.getProject().getName() + " found " + found.size());
            final Component f = frame;
            edt(() -> { if (f instanceof Frame) ((Frame) f).setExtendedState(Frame.MAXIMIZED_BOTH); });
            Thread.sleep(3000);
            DiagramManager dm = ApplicationManager.instance().getDiagramManager();
            int i = 0;
            for (Map.Entry<String, String> e : wanted.entrySet()) {
                i++;
                IDiagramUIModel d = found.get(e.getKey());
                if (d == null) { log("missing " + e.getKey()); continue; }
                for (int attempt = 0; ; attempt++) {
                    try { edt(() -> dm.openDiagram(d)); break; }
                    catch (Exception ex) { if (attempt == 2) throw ex; log("retry open " + ex); Thread.sleep(3000); }
                }
                Thread.sleep(2500);
                edt(() -> d.setSpecialZoom(IDiagramUIModel.SPECIAL_ZOOM_FIT_PAGE));
                Thread.sleep(11000);   // VP's "Diagram Patched" notice disappears after about 10 s
                final File target = new File(out, e.getValue());
                edt(() -> {
                    try { paint(f, target); } catch (Exception ex) { throw new RuntimeException(ex); }
                });
                log("saved " + target.getName());
            }
            if (dbsetup) edt(this::sqliteDefault);
            if (steps != null) clickPath(f, steps.split(">"), new File(out, stepsFile));
            log("done");
        } catch (Throwable t) {
            Throwable c = t;
            while (c.getCause() != null && c != c.getCause()) c = c.getCause();
            java.io.StringWriter w = new java.io.StringWriter();
            c.printStackTrace(new java.io.PrintWriter(w));
            log("error " + t + " caused by " + w.toString().replace("\n", " | "));
        } finally {
            log("exit");
            Runtime.getRuntime().halt(0);   // quit without saving anything
        }
    }

    /** The window as it is shown: a title strip with the window title, then the content painted at 2x. */
    private static void paint(Component frame, File target) throws Exception {
        Component root = frame instanceof RootPaneContainer ? ((RootPaneContainer) frame).getRootPane() : frame;
        String title = frame instanceof Frame ? ((Frame) frame).getTitle() : "";
        int scale = 2, bar = 28;
        int w = root.getWidth(), h = root.getHeight();
        java.awt.image.BufferedImage img =
            new java.awt.image.BufferedImage(w * scale, (h + bar) * scale, java.awt.image.BufferedImage.TYPE_INT_RGB);
        Graphics2D g = img.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        g.scale(scale, scale);
        g.setColor(new Color(0xE8E8E8));
        g.fillRect(0, 0, w, bar);
        g.setColor(new Color(0xC8C8C8));
        g.drawLine(0, bar - 1, w, bar - 1);
        Color[] dots = {new Color(0xFF5F57), new Color(0xFEBC2E), new Color(0x28C840)};
        for (int i = 0; i < 3; i++) { g.setColor(dots[i]); g.fillOval(12 + i * 20, 8, 12, 12); }
        g.setColor(new Color(0x303030));
        g.setFont(new Font("SansSerif", Font.BOLD, 13));
        FontMetrics fm = g.getFontMetrics();
        g.drawString(title, (w - fm.stringWidth(title)) / 2, 19);
        g.translate(0, bar);
        root.paint(g);
        g.dispose();
        javax.imageio.ImageIO.write(img, "png", target);
    }

    /**
     * VP asks "Do you want to recover the auto-saved project?" after an earlier automated run was stopped; those
     * projects are this tool's own temporary builds, so the answer is No.
     */
    private void dismissRecover() throws Exception {
        List<AbstractButton> no = new ArrayList<>();
        edt(() -> {
            for (Window w : Window.getWindows())
                if (w.isShowing() && w instanceof Dialog && "Recover Project".equals(((Dialog) w).getTitle())) {
                    List<Component> found = new ArrayList<>();
                    collect(w, "No", found);
                    for (Component c : found) if (c instanceof AbstractButton) no.add((AbstractButton) c);
                }
        });
        for (AbstractButton b : no) {
            SwingUtilities.invokeLater(b::doClick);
            log("answered No to Recover Project");
            Thread.sleep(2000);
        }
    }

    /** Waits for the dialogs a step opened, lists their fields and paints them over the window. */
    private void captureDialogs(Component frame, File target) throws Exception {
        dismissRecover();
        List<Window> dialogs = new ArrayList<>();
        for (int i = 0; i < 5 && dialogs.isEmpty(); i++) {
            Thread.sleep(1000);
            edt(() -> { for (Window w : Window.getWindows()) if (w.isShowing() && w != frame) dialogs.add(w); });
        }
        for (Window w : dialogs) {
            log("dialog " + (w instanceof Dialog ? ((Dialog) w).getTitle() : w.getClass().getName()) + " " + w.getBounds());
            edt(() -> describe(w, "  "));
        }
        edt(() -> {
            try { paintWithDialogs(frame, dialogs, target); } catch (Exception ex) { throw new RuntimeException(ex); }
        });
        log("saved " + target.getName());
    }

    /** Lists the labels, fields, buttons and choices of a dialog, so that the screenshot can be checked in the log. */
    private void describe(Component c, String indent) {
        String text = null;
        if (c instanceof JLabel) text = "label " + ((JLabel) c).getText();
        else if (c instanceof AbstractButton) text = c.getClass().getSimpleName() + " " + ((AbstractButton) c).getText()
            + (((AbstractButton) c).isSelected() ? " [selected]" : "");
        else if (c instanceof javax.swing.text.JTextComponent && !(c.getParent() instanceof JComboBox))
            text = "text " + ((javax.swing.text.JTextComponent) c).getText();
        else if (c instanceof JComboBox) text = "combo " + ((JComboBox<?>) c).getSelectedItem();
        if (text != null && c.isShowing() && !text.endsWith(" null") && !text.trim().endsWith("label"))
            log(indent + text.replace("\n", " "));
        if (c instanceof Container) for (Component k : ((Container) c).getComponents()) describe(k, indent);
    }

    /** The main window as in paint(), with every open dialog drawn on top at its place on the screen. */
    private static void paintWithDialogs(Component frame, List<Window> dialogs, File target) throws Exception {
        Component root = frame instanceof RootPaneContainer ? ((RootPaneContainer) frame).getRootPane() : frame;
        String title = frame instanceof Frame ? ((Frame) frame).getTitle() : "";
        int scale = 2, bar = 28;
        int w = root.getWidth(), h = root.getHeight();
        java.awt.image.BufferedImage img =
            new java.awt.image.BufferedImage(w * scale, (h + bar) * scale, java.awt.image.BufferedImage.TYPE_INT_RGB);
        Graphics2D g = img.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        g.scale(scale, scale);
        titleBar(g, title, 0, 0, w, bar);
        Graphics2D content = (Graphics2D) g.create();
        content.translate(0, bar);
        root.paint(content);
        content.dispose();
        Point origin = root.getLocationOnScreen();
        for (Window d : dialogs) {
            Component droot = d instanceof RootPaneContainer ? ((RootPaneContainer) d).getRootPane() : d;
            Point p = droot.getLocationOnScreen();
            int x = p.x - origin.x, y = p.y - origin.y + bar;
            int dw = droot.getWidth(), dh = droot.getHeight();
            g.setColor(new Color(0, 0, 0, 60));
            g.fillRect(x + 4, y - bar + 6, dw, dh + bar);
            titleBar(g, d instanceof Dialog ? ((Dialog) d).getTitle() : "", x, y - bar, dw, bar);
            Graphics2D dg = (Graphics2D) g.create();
            dg.translate(x, y);
            droot.paint(dg);
            dg.dispose();
            g.setColor(new Color(0x9A9A9A));
            g.drawRect(x, y - bar, dw - 1, dh + bar - 1);
        }
        g.dispose();
        javax.imageio.ImageIO.write(img, "png", target);
    }

    private static void titleBar(Graphics2D g, String title, int x, int y, int w, int bar) {
        g.setColor(new Color(0xE8E8E8));
        g.fillRect(x, y, w, bar);
        g.setColor(new Color(0xC8C8C8));
        g.drawLine(x, y + bar - 1, x + w, y + bar - 1);
        Color[] dots = {new Color(0xFF5F57), new Color(0xFEBC2E), new Color(0x28C840)};
        for (int i = 0; i < 3; i++) { g.setColor(dots[i]); g.fillOval(x + 12 + i * 20, y + 8, 12, 12); }
        g.setColor(new Color(0x303030));
        g.setFont(new Font("SansSerif", Font.BOLD, 13));
        FontMetrics fm = g.getFontMetrics();
        g.drawString(title, x + (w - fm.stringWidth(title)) / 2, y + 19);
    }

    /** Operates VP's window as a person would, one step after the other (see the class comment), then paints it. */
    private void clickPath(Component frame, String[] steps, File target) throws Exception {
        Component root = frame instanceof RootPaneContainer ? ((RootPaneContainer) frame).getRootPane() : frame;
        for (int n = 0; n < steps.length; n++) {
            String step = steps[n].trim();
            dismissRecover();
            if (step.startsWith("shot:")) {
                File shot = new File(out, step.substring(5));
                List<Window> open = new ArrayList<>();
                edt(() -> { for (Window w : Window.getWindows()) if (w.isShowing() && w != frame) open.add(w); });
                for (Window w : open) {
                    log("dialog " + (w instanceof Dialog ? ((Dialog) w).getTitle() : w.getClass().getName()));
                    edt(() -> describe(w, "  "));
                }
                edt(() -> { try { paintWithDialogs(frame, open, shot); } catch (Exception ex) { throw new RuntimeException(ex); } });
                log("saved " + shot.getName());
                continue;
            }
            if (step.startsWith("path=")) {
                final String dir = step.substring(5);
                edt(() -> { for (Window w : Window.getWindows()) if (w.isShowing() && w != frame) setPath(w, dir); });
                log("output folder " + dir);
                Thread.sleep(1000);
                continue;
            }
            if (step.startsWith("unless:")) {
                String[] p = step.substring(7).split("@", 2);
                if (find(p[0]) != null) { log("already showing " + p[0]); continue; }
                String[] xy = p[1].split(",");
                int px = Integer.parseInt(xy[0].trim()), py = Integer.parseInt(xy[1].trim());
                final int qx = px < 0 ? root.getWidth() + px : px, qy = py < 0 ? root.getHeight() + py : py;
                SwingUtilities.invokeLater(() -> clickAt(root, qx, qy));
                Thread.sleep(3000);
                continue;
            }
            boolean optional = step.startsWith("?");
            if (optional) step = step.substring(1);
            final boolean dropdown = step.startsWith("popup:");
            final String label = dropdown ? step.substring(6) : step;
            final Component pick = find(label);
            if (pick == null && optional) { log("skipped " + label); continue; }
            if (pick == null) {
                log("not found: " + label + "; short labels on screen:");
                edt(() -> { for (Window w : Window.getWindows()) if (w.isShowing()) listLabels(w); });
                return;
            }
            log((dropdown ? "open " : "click ") + label + " (" + pick.getClass().getName() + ")");
            SwingUtilities.invokeLater(() -> {   // a modal dialog keeps this call open until it closes
                try {
                    if (dropdown) call(pick, "doPopupClick");
                    else if (pick instanceof AbstractButton) ((AbstractButton) pick).doClick();
                    else if (hasMethod(pick, "doActionClick")) call(pick, "doActionClick");
                    else clickAt(pick, pick.getWidth() / 2, pick.getHeight() / 2);
                } catch (Throwable t) { log("click error " + label + " " + t); }
            });
            Thread.sleep(3000);
        }
        captureDialogs(frame, target);
    }

    /** The first enabled control on screen with that label, or null. */
    private Component find(String label) throws Exception {
        List<Component> hits = new ArrayList<>();
        edt(() -> { for (Window w : Window.getWindows()) if (w.isShowing()) collect(w, label, hits); });
        for (Component c : hits) if (c.isShowing() && c.isEnabled()) return c;
        return null;
    }

    /** A mouse click at x,y of a component (VP's message pane button has no label). */
    private void clickAt(Component root, int x, int y) {
        Component c = SwingUtilities.getDeepestComponentAt(root, x, y);
        if (c == null) { log("nothing at " + x + "," + y); return; }
        Point q = SwingUtilities.convertPoint(root, x, y, c);
        log("click at " + x + "," + y + " (" + c.getClass().getName() + ")");
        long t = System.currentTimeMillis();
        for (int id : new int[]{java.awt.event.MouseEvent.MOUSE_PRESSED, java.awt.event.MouseEvent.MOUSE_RELEASED,
                                java.awt.event.MouseEvent.MOUSE_CLICKED})
            c.dispatchEvent(new java.awt.event.MouseEvent(c, id, t, id == java.awt.event.MouseEvent.MOUSE_PRESSED
                ? java.awt.event.InputEvent.BUTTON1_DOWN_MASK : 0, q.x, q.y, 1, false, java.awt.event.MouseEvent.BUTTON1));
    }

    /** Types dir into the editable path box of a dialog (the box whose text is an absolute path). */
    private static void setPath(Component c, String dir) {
        if (c instanceof JComboBox && ((JComboBox<?>) c).isEditable()) {
            @SuppressWarnings("unchecked") JComboBox<Object> box = (JComboBox<Object>) c;
            Object item = box.getEditor().getItem();
            if (item != null && item.toString().startsWith("/")) { box.getEditor().setItem(dir); box.setSelectedItem(dir); }
        }
        if (c instanceof Container) for (Component k : ((Container) c).getComponents()) setPath(k, dir);
    }

    private static String textOf(Component c) {
        if (c instanceof AbstractButton) return ((AbstractButton) c).getText();
        if (c instanceof JLabel) return ((JLabel) c).getText();
        if (hasMethod(c, "doActionClick")) {   // Flamingo command buttons (VP's ribbon and its dropdown menus)
            try { return (String) c.getClass().getMethod("getText").invoke(c); } catch (Exception e) { return null; }
        }
        return null;
    }

    private static boolean hasMethod(Object o, String name) {
        try { o.getClass().getMethod(name); return true; } catch (NoSuchMethodException e) { return false; }
    }

    private void call(Object o, String name) {
        try { o.getClass().getMethod(name).invoke(o); } catch (Exception e) { log("call " + name + " failed " + e); }
    }

    private static boolean matches(String s, String label) {
        if (s == null) return false;
        s = s.replaceAll("<[^>]+>", "").replace("…", "...").trim();
        return s.equalsIgnoreCase(label) || s.replaceAll("\\.\\.\\.$", "").trim().equalsIgnoreCase(label);
    }

    private static void collect(Component c, String label, List<Component> hits) {
        if ((c instanceof AbstractButton || c instanceof JLabel || hasMethod(c, "doActionClick"))
            && (matches(textOf(c), label) || matches(c.getName(), label)
                || (c instanceof AbstractButton && matches(((AbstractButton) c).getActionCommand(), label))))
            hits.add(c instanceof JLabel && c.getParent() != null ? c.getParent() : c);
        if (c instanceof JTabbedPane)
            for (int i = 0; i < ((JTabbedPane) c).getTabCount(); i++)
                if (matches(((JTabbedPane) c).getTitleAt(i), label)) hits.add(c);
        if (c instanceof JMenu) for (Component k : ((JMenu) c).getMenuComponents()) collect(k, label, hits);
        if (c instanceof Container) for (Component k : ((Container) c).getComponents()) collect(k, label, hits);
    }

    private void listLabels(Component c) {
        String t = textOf(c);
        if (c.isShowing() && t != null && !t.isEmpty() && t.length() < 40)
            log("  " + c.getClass().getSimpleName() + " '" + t + "'");
        if (c instanceof Container) for (Component k : ((Container) c).getComponents()) listLabels(k);
    }

    /** SQLite becomes the default database of the project, as in Tools > DB > Database Configuration. */
    private void sqliteDefault() {
        ProjectManager pm = ApplicationManager.instance().getProjectManager();
        for (com.vp.plugin.model.DatabaseType t : com.vp.plugin.model.DatabaseType.values()) {
            try {
                com.vp.plugin.model.DatabaseSetting d =
                    pm.loadDatabaseSetting(pm.getProject(), t, com.vp.plugin.model.DatabaseLanguage.Java);
                if (d == null) continue;
                boolean sqlite = t == com.vp.plugin.model.DatabaseType.SQLite;
                if (sqlite) { d.setDriver("SQLite"); d.setDefault(true); d.setSupported(true); }   // VP's name of the driver
                else if (d.isDefault()) d.setDefault(false);
                else continue;
                pm.saveDatabaseSetting(pm.getProject(), t, com.vp.plugin.model.DatabaseLanguage.Java, d);
                log("database " + t + " default=" + d.isDefault() + " driver=" + d.getDriver());
            } catch (Throwable e) { log("database " + t + " error " + e); }
        }
    }
}
