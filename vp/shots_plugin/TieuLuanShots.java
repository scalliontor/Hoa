import com.vp.plugin.*;
import com.vp.plugin.diagram.IDiagramUIModel;
import java.awt.*;
import java.io.File;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;
import java.util.*;
import java.util.List;
import javax.swing.*;

/**
 * Screenshots of the Visual Paradigm window, for the diagram types the Community Edition cannot draw (BPMN,
 * DFD, ArchiMate): the essay shows them as screenshots of the trial edition rather than as watermarked exports.
 * Active only when shots.request exists next to this plugin:
 *   line 1      output folder (receives shots.log and the PNG files)
 *   xml=...     diagrams to build, in the format of vp/diagrams.xml (TieuLuanBuilder builds them in the window)
 *   name|file   one diagram per line
 * For each diagram the plugin opens it, zooms it to
 * the window and paints the window (with its title, e.g. "... Visual Paradigm Enterprise (Evaluation Copy)")
 * into a PNG at 2x; only VP's own window is painted, never the rest of the screen. VP then quits without saving.
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
            String xml = null;
            for (String l : lines.subList(1, lines.size())) {
                if (l.startsWith("xml=")) xml = l.substring(4).trim();
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
}
