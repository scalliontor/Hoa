import com.vp.plugin.*;
import com.vp.plugin.diagram.*;
import com.vp.plugin.diagram.connector.*;
import com.vp.plugin.diagram.shape.*;
import com.vp.plugin.model.*;
import com.vp.plugin.model.factory.IModelElementFactory;
import java.awt.Color;
import java.awt.Font;
import java.awt.Point;
import java.awt.Rectangle;
import java.io.File;
import java.util.*;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

/**
 * Builds the essay's editable Visual Paradigm project from vp/diagrams.xml.
 *
 * Every figure of the essay is a real VP diagram: the XML only fixes element
 * names, coordinates and connector routes, so the result can be opened and
 * edited in Visual Paradigm like any hand-drawn project.
 */
public final class TieuLuanBuilder implements VPPlugin, VPPluginCommandLineSupport {
    private final File root = new File(System.getProperty("tieuluan.root"));
    /** Input XML and export folder; overridable so test builds never touch the essay figures. */
    private final File xml = System.getProperty("tieuluan.xml") != null
        ? new File(System.getProperty("tieuluan.xml")) : new File(root, "vp/diagrams.xml");
    private final File out = System.getProperty("tieuluan.out") != null
        ? new File(System.getProperty("tieuluan.out")) : new File(root, "figures/vp");
    private DiagramManager dm;
    private IModelElementFactory factory;
    /** Actors and classes that appear in several diagrams share one model element. */
    private final Map<String, IModelElement> shared = new HashMap<>();
    private final Set<String> stereotyped = new HashSet<>();
    /** Classes whose members were already created (a lifeline may create a class before it is drawn). */
    private final Set<String> withMembers = new HashSet<>();

    @Override public void loaded(VPPluginInfo info) { }
    @Override public void unloaded() { }

    @Override public void invoke(String[] args) {
        try {
            dm = ApplicationManager.instance().getDiagramManager();
            factory = IModelElementFactory.instance();
            ProjectManager pm = ApplicationManager.instance().getProjectManager();
            // The command line opens a seed project; a fresh project would need a
            // Swing dialog in headless mode, so the seed's elements are removed.
            List<IModelElement> old = new ArrayList<>();
            Iterator<?> it = pm.getProject().modelElementIterator();
            while (it.hasNext()) old.add((IModelElement) it.next());
            for (IModelElement element : old) {
                try { element.delete(); } catch (UnsupportedOperationException ignored) { }
            }
            Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(xml);
            Element top = doc.getDocumentElement();
            for (Element spec : children(top, "diagram")) new DiagramBuild(spec).run();
            // VP's own SQL generator on the tables of the physical model (the ERD), when asked for.
            String ddl = System.getProperty("tieuluan.ddl");
            if (ddl != null) generateDdl(new File(ddl));
            File target = new File(top.getAttribute("project"));
            if (!target.isAbsolute()) target = new File(root, top.getAttribute("project"));
            if (!pm.saveProjectAs(target)) throw new IllegalStateException("Cannot save " + target);
            System.out.println("TIEULUAN_BUILD_SUCCESS " + target.getAbsolutePath());
        } catch (Throwable error) {
            error.printStackTrace();
            throw new RuntimeException(error);
        }
    }

    /** CREATE TABLE statements written by Visual Paradigm (DatabaseManager, SQLite dialect) for every DB table. */
    private void generateDdl(File file) throws Exception {
        List<IModelElement> tables = new ArrayList<>();
        Iterator<?> it = ApplicationManager.instance().getProjectManager().getProject()
            .allLevelModelElementIterator(IModelElementFactory.MODEL_TYPE_DB_TABLE);
        while (it.hasNext()) tables.add((IModelElement) it.next());
        // The project's database configuration (Tools > DB > Database Configuration): SQLite with the driver of the demo.
        DatabaseSetting setting = new DatabaseSetting();
        // VP writes every field of the setting into the project file; a null field breaks its XML.
        for (java.lang.reflect.Method m : DatabaseSetting.class.getMethods())
            if (m.getName().startsWith("set") && m.getParameterCount() == 1 && m.getParameterTypes()[0] == String.class)
                m.invoke(setting, "");
        setting.setDialect(DatabaseSetting.DIALECT_SQLITE);
        setting.setDriver(DatabaseSetting.DRIVER_SQLITE);
        setting.setDriverClass(DatabaseSetting.DRIVER_SQLITE);
        setting.setDriverFiles(new File(root, "demo/lib/sqlite-jdbc-3.46.1.3.jar").getAbsolutePath());
        setting.setConnectionURL("jdbc:sqlite:" + new File(file.getParentFile(), "vp_generated.db").getAbsolutePath());
        setting.setSupported(true);
        setting.setDefault(true);
        ProjectManager pm = ApplicationManager.instance().getProjectManager();
        pm.saveDatabaseSetting(pm.getProject(), DatabaseType.SQLite, DatabaseLanguage.Java, setting);
        String sql = ApplicationManager.instance().getDatabaseManager()
            .generateCreateSQL(DatabaseType.SQLite, tables.toArray(new IModelElement[0]));
        if (sql == null || sql.trim().isEmpty()) throw new IllegalStateException("VP generated no SQL");
        file.getParentFile().mkdirs();
        java.nio.file.Files.write(file.toPath(), sql.getBytes("UTF-8"));
        System.out.println("TIEULUAN_DDL " + tables.size() + " tables -> " + file.getAbsolutePath());
    }

    // ------------------------------------------------------------------ XML

    private static List<Element> children(Element parent, String tag) {
        List<Element> result = new ArrayList<>();
        NodeList nodes = parent.getChildNodes();
        for (int i = 0; i < nodes.getLength(); i++) {
            Node node = nodes.item(i);
            if (node instanceof Element && (tag == null || ((Element) node).getTagName().equals(tag)))
                result.add((Element) node);
        }
        return result;
    }

    private static int num(Element e, String key, int fallback) {
        return e.hasAttribute(key) ? (int) Math.round(Double.parseDouble(e.getAttribute(key))) : fallback;
    }

    private static boolean yes(Element e, String key) { return "true".equals(e.getAttribute(key)); }

    private static String text(Element e, String key) { return e.hasAttribute(key) ? e.getAttribute(key) : null; }

    private static Point[] points(Element e) {
        List<Point> list = new ArrayList<>();
        for (Element p : children(e, "pt")) list.add(new Point(num(p, "x", 0), num(p, "y", 0)));
        return list.isEmpty() ? null : list.toArray(new Point[0]);
    }

    // -------------------------------------------------------------- diagram

    private final class DiagramBuild {
        final Element spec;
        final String id;
        final String kind;
        final int fontSize;
        final String fontName;
        /** Diagrams with the same scope share classes and packages; other scopes get their own copies. */
        final String scope;
        IDiagramUIModel diagram;
        IPackage scopePackage;
        final Map<String, IModelElement> models = new HashMap<>();
        final Map<String, IShapeUIModel> views = new HashMap<>();
        /** Swimlane bookkeeping: lane index to partition and compartment. */
        IActivitySwimlane2 swim;
        final List<IActivityPartition> partitions = new ArrayList<>();
        final List<IShapeUIModel> cells = new ArrayList<>();
        /** ERD bookkeeping: column specs per table, used to name the columns VP adds for foreign keys. */
        final Map<String, Map<String, Element>> columnSpecs = new HashMap<>();
        /** Label rectangles placed by the XML; the export area must include them. */
        final List<Rectangle> labels = new ArrayList<>();

        DiagramBuild(Element spec) {
            this.spec = spec;
            this.id = spec.getAttribute("id");
            this.kind = spec.getAttribute("kind");
            // 0 = keep Visual Paradigm's default font.
            this.fontSize = num(spec, "font", 0);
            this.fontName = spec.hasAttribute("fontName") ? spec.getAttribute("fontName") : "Arial";
            this.scope = spec.hasAttribute("scope") ? spec.getAttribute("scope") : id;
        }

        void run() throws Exception {
            String type;
            if (spec.hasAttribute("scopeName")) {
                scopePackage = (IPackage) shared.get("Scope:" + scope);
                if (scopePackage == null) {
                    scopePackage = factory.createPackage();
                    scopePackage.setName(spec.getAttribute("scopeName"));
                    shared.put("Scope:" + scope, scopePackage);
                }
            }
            switch (kind) {
                case "usecase": type = IDiagramTypeConstants.DIAGRAM_TYPE_USE_CASE_DIAGRAM; break;
                case "class": type = IDiagramTypeConstants.DIAGRAM_TYPE_CLASS_DIAGRAM; break;
                case "erd": type = "ERDiagram"; break;
                case "object": type = IDiagramTypeConstants.DIAGRAM_TYPE_OBJECT_DIAGRAM; break;
                case "activity": type = IDiagramTypeConstants.DIAGRAM_TYPE_ACTIVITY_DIAGRAM; break;
                case "sequence": type = IDiagramTypeConstants.DIAGRAM_TYPE_INTERACTION_DIAGRAM; break;
                case "state": type = IDiagramTypeConstants.DIAGRAM_TYPE_STATE_DIAGRAM; break;
                case "flowchart": type = "Flowchart"; break;
                case "dfd": type = "GaneSarsonDFD"; break;
                case "deployment": type = IDiagramTypeConstants.DIAGRAM_TYPE_DEPLOYMENT_DIAGRAM; break;
                // Any other VP diagram type by its name (BusinessProcessDiagram, DataFlowDiagram, ArchiMate4Diagram...).
                case "raw": type = spec.getAttribute("vptype"); break;
                default: throw new IllegalArgumentException("Unknown diagram kind " + kind);
            }
            diagram = dm.createDiagram(type);
            diagram.setName(spec.getAttribute("name"));
            if (diagram instanceof IUseCaseDiagramUIModel) {
                IUseCaseDiagramUIModel uc = (IUseCaseDiagramUIModel) diagram;
                uc.setShowExtendCondition(true);
                uc.setShowUseCaseExtensionPoint(false);
            }
            if (diagram instanceof IInteractionDiagramUIModel) {
                IInteractionDiagramUIModel seq = (IInteractionDiagramUIModel) diagram;
                seq.setShowDiagramFrame(false);
                seq.setShowActivations(true);
                seq.setShowSequenceNumbers(yes(spec, "numbers"));
                if (yes(spec, "numbers")) seq.setRequestRecalculateSequenceNumbers(true);
            }
            if (diagram instanceof IERDiagramUIModel) {
                IERDiagramUIModel er = (IERDiagramUIModel) diagram;
                er.setDataModel(2);
                er.setShowColumnTypes(true);
                er.setShowColumnUserType(true);
            }
            for (Element node : children(spec, "node")) node(node);
            // Model-only ownership: put classes drawn in other diagrams into this diagram's packages.
            for (Element c : children(spec, "contain")) {
                IModelElement owner = models.get(c.getAttribute("package"));
                IModelElement member = shared.get(scope + "/Class:" + c.getAttribute("class"));
                if (owner == null || member == null)
                    throw new IllegalStateException(id + ": cannot contain " + c.getAttribute("class"));
                tryAddChild(owner, member);
            }
            for (Element edge : children(spec, "edge")) edge(edge);
            for (Element act : children(spec, "activation")) activation(act);
            // Extend connectors add an extension point to the base use case; keep the ellipses plain.
            for (IShapeUIModel view : views.values())
                if (view instanceof IUseCaseUIModel) ((IUseCaseUIModel) view).setShowExtensionPoint(false);

            if ("orthogonal".equals(spec.getAttribute("route")))
                dm.layout(diagram, DiagramManager.LAYOUT_ROUTE_CONNECTORS_ORTHOGONAL);
            if (!"false".equals(spec.getAttribute("export"))) export();
            if (yes(spec, "debug")) debug();
            System.out.println("BUILT " + id + " nodes=" + models.size()
                + " edges=" + children(spec, "edge").size());
        }

        // ------------------------------------------------------------ nodes

        void font(IDiagramElement element) {
            if (fontSize > 0) element.getElementFont().setValues(fontName, Font.PLAIN, fontSize, Color.BLACK);
            element.setRequestResetCaption(true);
        }

        void fill(IShapeUIModel view, Element node) {
            if (!node.hasAttribute("fill")) return;
            Color color = Color.decode(node.getAttribute("fill"));
            view.setBackground(color);
            view.getFillColor().setColor1(color, true);
        }

        IModelElement sharedModel(String key, String type, String name) {
            if (!key.startsWith("Actor:")) key = scope + "/" + key;
            IModelElement model = shared.get(key);
            if (model == null) {
                model = factory.create(type);
                if (model == null) throw new IllegalStateException("Cannot create " + type);
                model.setName(name);
                shared.put(key, model);
            }
            return model;
        }

        void node(Element n) {
            String nid = n.getAttribute("id");
            String type = n.getAttribute("type");
            String name = n.hasAttribute("name") ? n.getAttribute("name") : "";
            IModelElement model;
            IShapeUIModel view;
            try {
                switch (type) {
                    case "Swimlane": swimlane(n); return;
                    case "Actor": {
                        model = sharedModel("Actor:" + name, "Actor", name);
                        view = (IShapeUIModel) dm.createDiagramElement(diagram, model);
                        break;
                    }
                    case "SeqActor": {
                        model = sharedModel("Actor:" + name, "Actor", name);
                        view = (IShapeUIModel) dm.createDiagramElement(diagram, "InteractionActor");
                        view.setModelElement(model);
                        break;
                    }
                    case "Package": {
                        // Keyed by node id: two layers may both own a package called "search".
                        model = sharedModel("Package:" + nid, "Package", name);
                        view = (IShapeUIModel) dm.createDiagramElement(diagram, model);
                        break;
                    }
                    case "DBTable": {
                        IDBTable table = factory.createDBTable();
                        // Own the table before its shape exists; re-parenting later breaks the entity layout.
                        if (scopePackage != null) scopePackage.addChild(table);
                        table.setDataModel(2);
                        table.setName(name);
                        // Columns must exist before the shape is drawn; VP appends each foreign-key column later.
                        Map<String, Element> specs = new LinkedHashMap<>();
                        for (Element c : children(n, "column")) {
                            specs.put(c.getAttribute("name"), c);
                            if (!c.hasAttribute("fk")) column(table.createDBColumn(), c);
                        }
                        columnSpecs.put(nid, specs);
                        model = table;
                        view = (IShapeUIModel) dm.createDiagramElement(diagram, model);
                        break;
                    }
                    case "Class": {
                        model = sharedModel("Class:" + name, "Class", name);
                        if (withMembers.add(scope + "/Class:" + name)) classMembers((IClass) model, n);
                        view = (IShapeUIModel) dm.createDiagramElement(diagram, model);
                        if (view instanceof IClassUIModel) {
                            IClassUIModel cv = (IClassUIModel) view;
                            cv.setShowDerivedAttributes(true);
                            if (yes(n, "hideMembers")) {
                                cv.setShowAttributeType(IClassUIModel.ATTR_SHOW_TYPE_NONE);
                                cv.setShowOperationType(IClassUIModel.OP_SHOW_TYPE_NONE);
                                cv.setShowEnumerationLiteralType(IClassUIModel.ENUMERATION_LITERAL_SHOW_TYPE_NONE);
                            }
                            if (yes(n, "hideOperations"))
                                cv.setShowOperationType(IClassUIModel.OP_SHOW_TYPE_NONE);
                            if (yes(n, "hideAttributes"))
                                cv.setShowAttributeType(IClassUIModel.ATTR_SHOW_TYPE_NONE);
                            if ("false".equals(n.getAttribute("signature"))) cv.setShowOperationSignature(false);
                            if (n.hasAttribute("opParams")) cv.setShowOperationsParameters(num(n, "opParams", 0));
                            if (n.hasAttribute("hideOps")) {
                                // Hidden lists only apply when the show type is CUSTOMIZED.
                                List<String> names = Arrays.asList(n.getAttribute("hideOps").split(","));
                                List<IOperation> hidden = new ArrayList<>();
                                for (IOperation op : ((IClass) model).toOperationArray())
                                    if (names.contains(op.getName())) hidden.add(op);
                                cv.setShowOperationType(IClassUIModel.OP_SHOW_TYPE_CUSTOMIZED);
                                cv.setHiddenOperationModels(hidden.toArray(new IOperation[0]));
                            }
                        }
                        break;
                    }
                    case "Instance": {
                        IInstanceSpecification inst = factory.createInstanceSpecification();
                        inst.setName(name);
                        IClass classifier = (IClass) shared.get(scope + "/Class:" + n.getAttribute("classifier"));
                        if (classifier == null)
                            throw new IllegalStateException("Unknown classifier " + n.getAttribute("classifier"));
                        inst.addClassifier(classifier);
                        for (Element s : children(n, "slot")) slot(inst, classifier, s);
                        model = inst;
                        view = (IShapeUIModel) dm.createDiagramElement(diagram, model);
                        break;
                    }
                    case "Lifeline": {
                        IInteractionLifeLine line = factory.createInteractionLifeLine();
                        line.setName(name);
                        if (n.hasAttribute("classifier")) {
                            // The class may be drawn (with its members) by a later diagram of the same scope.
                            String cname = n.getAttribute("classifier");
                            IModelElement classifier = sharedModel("Class:" + cname, "Class", cname);
                            if (scopePackage != null && classifier.getParent() != scopePackage
                                    && (classifier.getParent() == null || classifier.getParent() == scopePackage.getParent()))
                                scopePackage.addChild(classifier);
                            line.setBaseClassifier(classifier);
                        }
                        model = line;
                        view = (IShapeUIModel) dm.createDiagramElement(diagram, model);
                        break;
                    }
                    case "Fragment": { fragment(n); return; }
                    case "Note": {
                        INOTE note = factory.createNOTE();
                        note.setDescription(name);
                        model = note;
                        view = (IShapeUIModel) dm.createDiagramElement(diagram, model);
                        break;
                    }
                    default: {
                        String modelType = modelType(type);
                        model = factory.create(modelType);
                        if (model == null) throw new IllegalStateException("Cannot create " + modelType);
                        model.setName(name);
                        view = (IShapeUIModel) dm.createDiagramElement(diagram, model);
                    }
                }
                if (view == null) throw new IllegalStateException("No view for " + type);
                // A shared element keeps the stereotypes it received in its first diagram.
                if (n.hasAttribute("stereotype") && stereotyped.add(model.getId()))
                    for (String s : n.getAttribute("stereotype").split(","))
                        model.addStereotype(s.trim());
                if (scopePackage != null && !n.hasAttribute("parent") && !(model instanceof IActor)
                        && (model.getParent() == null || model.getParent() == scopePackage.getParent()))
                    scopePackage.addChild(model);
                if (model instanceof IClass && yes(n, "abstract")) ((IClass) model).setAbstract(true);
                if (model instanceof IUseCase && yes(n, "abstract")) ((IUseCase) model).setAbstract(true);
                if (model instanceof IGsDfdProcess && n.hasAttribute("number"))
                    ((IGsDfdProcess) model).setDfId(n.getAttribute("number"));
                // DFD: process number and data store id; BPMN: message events.
                if (model instanceof IDFProcess && n.hasAttribute("number")) ((IDFProcess) model).setDfId(n.getAttribute("number"));
                if (model instanceof IDFDataStore && n.hasAttribute("number")) ((IDFDataStore) model).setDfId(n.getAttribute("number"));
                if ("message".equals(n.getAttribute("trigger"))) {
                    IModelElement trigger = factory.create("BPMessageTrigger");
                    if (model instanceof IBPStartEvent) ((IBPStartEvent) model).setTrigger(trigger);
                    if (model instanceof IBPIntermediateEvent) ((IBPIntermediateEvent) model).setTrigger(trigger);
                }
                if (view instanceof com.vp.plugin.diagram.shape.IBPPoolUIModel) {
                    com.vp.plugin.diagram.shape.IBPPoolUIModel pool = (com.vp.plugin.diagram.shape.IBPPoolUIModel) view;
                    pool.setAutoStretch(com.vp.plugin.diagram.shape.IBPPoolUIModel.AUTO_STRETCH_OFF);
                    if (yes(n, "blackBox")) pool.setBlackBox(com.vp.plugin.diagram.shape.IBPPoolUIModel.BLACK_BOX_YES);
                }
                if (n.hasAttribute("doc")) model.setDocumentation(n.getAttribute("doc"));

                // Containment: use cases sit in their system, classes in packages,
                // activity nodes in a swimlane compartment.
                String parent = text(n, "parent");
                if (parent != null) {
                    IModelElement owner = models.get(parent);
                    IShapeUIModel ownerView = views.get(parent);
                    if (owner == null || ownerView == null)
                        throw new IllegalStateException("Unknown parent " + parent);
                    if (model instanceof IBPLane && owner instanceof IBPPool) ((IBPPool) owner).addBPLane((IBPLane) model);
                    else if (!(model instanceof IActor) || !shared.containsValue(model) || owner instanceof IPackage)
                        tryAddChild(owner, model);
                    // nest="false": owned by the package in the model, drawn on top of it without nesting views.
                    if (!"false".equals(n.getAttribute("nest"))) ownerView.addChild(view);
                }
                if (n.hasAttribute("lane")) {
                    int lane = num(n, "lane", 0);
                    swim.addChild(model);
                    partitions.get(lane).addContainedElement(model);
                    cells.get(lane).addChild(view);
                }
                view.setBounds(num(n, "x", 0), num(n, "y", 0), num(n, "w", 120), num(n, "h", 60));
                font(view);
                fill(view, n);
                if (yes(n, "transparent")) view.getFillColor().setTransparency(100, true);
                if (view instanceof IDBTableUIModel)   // every column, including the foreign keys VP adds later
                    ((IDBTableUIModel) view).setShowColumnsMode(IDBTableUIModel.SHOW_COLUMNS_MODE_SHOW_ALL);
                if ("false".equals(n.getAttribute("nest"))) view.bringToFront();
                if (n.hasAttribute("captionX")) {
                    view.getCaptionUIModel().setBounds(num(n, "captionX", 0), num(n, "captionY", 0),
                        num(n, "captionW", 140), num(n, "captionH", 22));
                }
                if (view instanceof IInteractionLifeLineUIModel && n.hasAttribute("classifier"))
                    ((IInteractionLifeLineUIModel) view).setShowClassifier(true);
                models.put(nid, model);
                views.put(nid, view);
            } catch (RuntimeException error) {
                throw new IllegalStateException(id + "/" + nid + ": " + error.getMessage(), error);
            }
        }

        void column(IDBColumn column, Element c) {
            column.setName(c.getAttribute("name"));
            String type = c.getAttribute("type");
            boolean known = column.setType(type, num(c, "length", 0), num(c, "scale", 0));
            String shown = String.valueOf(column.getTypeInText()).toLowerCase();
            // VP maps an unknown type (bytea) to integer: keep the type of the schema as a user type instead.
            if (!known || !shown.startsWith(type.toLowerCase())) column.setUserType(type);
            if (c.hasAttribute("length")) column.setLength(num(c, "length", 0));
            if (c.hasAttribute("scale")) column.setScale(num(c, "scale", 0));
            column.setNullable(yes(c, "nullable"));
            column.setPrimaryKey(yes(c, "pk"));
            if (yes(c, "unique")) column.setUnique(true);
        }

        void tryAddChild(IModelElement owner, IModelElement child) {
            if (owner instanceof IHasChildrenBaseModelElement)
                ((IHasChildrenBaseModelElement) owner).addChild(child);
        }

        String modelType(String type) {
            switch (type) {
                case "Initial": return "InitialNode";
                case "Final": return "ActivityFinalNode";
                case "FlowFinal": return "FlowFinalNode";
                case "Action": return "ActivityAction";
                case "Decision": return "DecisionNode";
                case "Merge": return "MergeNode";
                case "Fork": return "ForkNode";
                case "Join": return "JoinNode";
                case "ObjectNode": return "ActivityObject";
                case "InitialState": return "InitialPseudoState";
                case "State": return "State2";
                case "FinalState": return "FinalState2";
                default: return type;
            }
        }

        void classMembers(IClass cls, Element n) {
            for (Element a : children(n, "attr")) {
                IAttribute attribute = cls.createAttribute();
                attribute.setName(a.getAttribute("name"));
                if (a.hasAttribute("type")) attribute.setType(a.getAttribute("type"));
                attribute.setVisibility(a.hasAttribute("vis") ? a.getAttribute("vis") : "private");
                if (yes(a, "derived")) attribute.setDerived(true);
                if (a.hasAttribute("mult")) attribute.setMultiplicity(a.getAttribute("mult"));
            }
            for (Element l : children(n, "literal")) cls.createEnumerationLiteral().setName(l.getAttribute("name"));
            for (Element o : children(n, "op")) {
                IOperation operation = cls.createOperation();
                operation.setName(o.getAttribute("name"));
                operation.setVisibility(o.hasAttribute("vis") ? o.getAttribute("vis") : "public");
                if (o.hasAttribute("ret")) operation.setReturnType(o.getAttribute("ret"));
                if (yes(o, "static")) operation.setScope(IOperation.SCOPE_CLASSIFIER);
                if (yes(o, "abstract")) operation.setAbstract(true);
                if (o.hasAttribute("params")) {
                    // ";" separates parameters: generic types such as Map<String, Object> contain commas.
                    for (String p : o.getAttribute("params").split(";")) {
                        if (p.trim().isEmpty()) continue;
                        String[] parts = p.split(":", 2);
                        IParameter parameter = factory.createParameter();
                        parameter.setName(parts[0].trim());
                        if (parts.length > 1) parameter.setType(parts[1].trim());
                        operation.addParameter(parameter);
                    }
                }
            }
        }

        void slot(IInstanceSpecification inst, IClass classifier, Element s) {
            IAttribute feature = findAttribute(classifier, s.getAttribute("feature"));
            if (feature == null)
                throw new IllegalStateException("No attribute " + s.getAttribute("feature") + " in " + classifier.getName());
            ISlot slot = factory.createSlot();
            slot.setFeature(feature);
            ICompositeValueSpecification value = factory.createCompositeValueSpecification();
            value.setValue(s.getAttribute("value"));
            slot.addValue(value);
            inst.addSlot(slot);
        }

        /** Own attribute first, then the attributes inherited through generalizations. */
        IAttribute findAttribute(IClass cls, String name) {
            for (IAttribute a : cls.toAttributeArray())
                if (a.getName().equals(name)) return a;
            // VP stores a generalization with the parent as "from" and the child as "to".
            for (ISimpleRelationship r : cls.toToRelationshipArray()) {
                if (r instanceof IGeneralization && ((IGeneralization) r).getFrom() instanceof IClass) {
                    IAttribute inherited = findAttribute((IClass) ((IGeneralization) r).getFrom(), name);
                    if (inherited != null) return inherited;
                }
            }
            return null;
        }

        void swimlane(Element n) {
            swim = factory.createActivitySwimlane2();
            IActivitySwimlane2NewUIModel swimView =
                (IActivitySwimlane2NewUIModel) dm.createDiagramElement(diagram, swim);
            int x0 = num(n, "x", 20), y0 = num(n, "y", 20);
            int header = num(n, "header", 34), body = num(n, "h", 800) - header;
            List<Element> lanes = children(n, "lane");
            int total = 0;
            for (Element lane : lanes) total += num(lane, "w", 260);
            swimView.setBounds(x0, y0, total, header + body);
            String[] headerIds = new String[lanes.size()];
            String[] cellIds = new String[lanes.size()];
            int x = x0;
            for (int i = 0; i < lanes.size(); i++) {
                int w = num(lanes.get(i), "w", 260);
                IActivityPartition partition = factory.createActivityPartition();
                partition.setName(lanes.get(i).getAttribute("name"));
                swim.addVerticalPartition(partition);
                swim.addChild(partition);
                IActivityPartitionHeaderUIModel head =
                    (IActivityPartitionHeaderUIModel) dm.createDiagramElement(diagram, partition);
                head.setHorizontal(false);
                head.setSwimlane(swimView);
                head.setBounds(x, y0, w, header);
                font(head);
                swimView.addChild(head);
                headerIds[i] = head.getId();
                IActivitySwimlane2CompartmentUIModel cell = (IActivitySwimlane2CompartmentUIModel)
                    dm.createDiagramElement(diagram, IShapeTypeConstants.SHAPE_TYPE_ACTIVITY_SWIMLANE2_COMPARTMENT);
                cell.setVerticalPartitionId(head.getId());
                cell.setBounds(x, y0 + header, w, body);
                swimView.addChild(cell);
                cellIds[i] = cell.getId();
                partitions.add(partition);
                cells.add(cell);
                x += w;
            }
            swimView.setVerticalPartitionIds(headerIds);
            swimView.setCompartmentIds(cellIds);
            models.put(n.getAttribute("id"), swim);
            views.put(n.getAttribute("id"), swimView);
            // Header captions are local to their header shape.
            for (int i = 0; i < lanes.size(); i++) {
                IShapeUIModel head = (IShapeUIModel) diagram.getDiagramElementById(headerIds[i]);
                head.getCaptionUIModel().setBounds(6, (header - 22) / 2, head.getWidth() - 12, 22);
            }
        }

        void fragment(Element n) {
            ICombinedFragment fragment = factory.createCombinedFragment();
            fragment.setInteractionOperator(n.getAttribute("operator"));
            IShapeUIModel view = (IShapeUIModel) dm.createDiagramElement(diagram, fragment);
            int x = num(n, "x", 0), y = num(n, "y", 0), w = num(n, "w", 400), h = num(n, "h", 200);
            view.setBounds(x, y, w, h);
            font(view);
            if (yes(n, "transparent")) view.getFillColor().setTransparency(100, true);
            view.setCoverConnector(false);
            for (String covered : n.getAttribute("covers").split(",")) {
                IModelElement line = models.get(covered.trim());
                if (line instanceof IInteractionLifeLine) fragment.addCoveredLifeLine(line);
            }
            List<Element> operands = children(n, "operand");
            for (int i = 0; i < operands.size(); i++) {
                Element o = operands.get(i);
                IInteractionOperand operand = fragment.createInteractionOperand();
                IInteractionConstraint guard = factory.createInteractionConstraint();
                guard.setConstraint(o.getAttribute("guard"));
                operand.setGuard(guard);
                IShapeUIModel ov = (IShapeUIModel) dm.createDiagramElement(diagram, operand);
                view.addChild(ov);
                int oy = num(o, "y", y + 24), oh = num(o, "h", h - 24);
                ov.setBounds(x + 4, oy, w - 8, oh);
                font(ov);
                if (yes(n, "transparent")) ov.getFillColor().setTransparency(100, true);
            }
            models.put(n.getAttribute("id"), fragment);
            views.put(n.getAttribute("id"), view);
        }

        void activation(Element a) {
            IModelElement line = models.get(a.getAttribute("on"));
            IShapeUIModel lineView = views.get(a.getAttribute("on"));
            if (!(line instanceof IInteractionLifeLine))
                throw new IllegalStateException(id + ": activation on unknown lifeline " + a.getAttribute("on"));
            IActivation activation = factory.createActivation();
            ((IInteractionLifeLine) line).addActivation(activation);
            IShapeUIModel view = (IShapeUIModel) dm.createDiagramElement(diagram, activation);
            int cx = lineView.getX() + lineView.getWidth() / 2;
            int y1 = num(a, "y1", 0), y2 = num(a, "y2", 0);
            view.setBounds(cx - IActivationUIModel.BODY_WIDTH / 2, y1, IActivationUIModel.BODY_WIDTH, y2 - y1);
        }

        // ------------------------------------------------------------ edges

        void edge(Element e) {
            String type = e.getAttribute("type");
            String from = e.getAttribute("from"), to = e.getAttribute("to");
            IModelElement fm = models.get(from), tm = models.get(to);
            IShapeUIModel fv = views.get(from), tv = views.get(to);
            if (fm == null || tm == null || fv == null || tv == null)
                throw new IllegalStateException(id + ": edge " + from + " -> " + to + " has an unknown end");
            Point[] route = points(e);
            IDiagramElement line;
            try {
                switch (type) {
                    case "Association": {
                        IAssociation r = factory.createAssociation();
                        r.setFrom(fm); r.setTo(tm);
                        if (e.hasAttribute("name")) r.setName(e.getAttribute("name"));
                        IAssociationEnd fe = (IAssociationEnd) r.getFromEnd(), te = (IAssociationEnd) r.getToEnd();
                        if (e.hasAttribute("fromMult")) fe.setMultiplicity(e.getAttribute("fromMult"));
                        if (e.hasAttribute("toMult")) te.setMultiplicity(e.getAttribute("toMult"));
                        if (e.hasAttribute("fromRole")) fe.setName(e.getAttribute("fromRole"));
                        if (e.hasAttribute("toRole")) te.setName(e.getAttribute("toRole"));
                        if ("composite".equals(e.getAttribute("aggregation")))
                            fe.setAggregationKind(IAssociationEnd.AGGREGATION_KIND_COMPOSITED);
                        if ("shared".equals(e.getAttribute("aggregation")))
                            fe.setAggregationKind(IAssociationEnd.AGGREGATION_KIND_SHARED);
                        if (yes(e, "direction")) r.setDirection(IAssociation.DIRECTION_FROM_TO);
                        if (yes(e, "navigable")) te.setNavigable(IAssociationEnd.NAVIGABLE_NAVIGABLE);
                        if ("non".equals(e.getAttribute("fromNav"))) fe.setNavigable(IAssociationEnd.NAVIGABLE_NON_NAVIGABLE);
                        line = dm.createConnector(diagram, r, fv, tv, route);
                        if (e.hasAttribute("arrows") && line instanceof IAssociationUIModel)
                            ((IAssociationUIModel) line).setShowNavigationArrows(num(e, "arrows", 0));
                        break;
                    }
                    case "DBForeignKey": {
                        IDBForeignKey fk = factory.createDBForeignKey();
                        fk.setDataModel(2);
                        if (e.hasAttribute("name")) fk.setName(e.getAttribute("name"));
                        fk.setFrom(fm); fk.setTo(tm);
                        fk.setFromMultiplicity(e.getAttribute("fromMult"));
                        fk.setToMultiplicity(e.getAttribute("toMult"));
                        fk.setIdentifying(yes(e, "identifying"));
                        line = dm.createConnector(diagram, fk, fv, tv, route);
                        // VP adds the referencing column itself; rename and type it after the spec.
                        String wanted = e.getAttribute("toColumn");
                        Element c = columnSpecs.get(to).get(wanted);
                        for (IDBColumn column : ((IDBTable) tm).toDBColumnArray())
                            for (IDBForeignKeyConstraint con : column.toForeignKeyConstraintArray())
                                if (con.getForeignKey().getId().equals(fk.getId())) {
                                    column.setForeignKeyNamePattern(wanted);
                                    column.setDbColumnName(wanted);
                                    column(column, c);
                                }
                        break;
                    }
                    case "Realization":
                    case "Generalization": {
                        // XML follows UML (child -> parent); VP stores the parent as "from".
                        IRelationship r = "Realization".equals(type) ? factory.createRealization() : factory.createGeneralization();
                        r.setFrom(tm); r.setTo(fm);
                        Point[] reversed = null;
                        if (route != null) {
                            reversed = route.clone();
                            Collections.reverse(Arrays.asList(reversed));
                        }
                        line = dm.createConnector(diagram, r, tv, fv, reversed);
                        break;
                    }
                    case "Dependency": {
                        IDependency r = factory.createDependency();
                        r.setFrom(fm); r.setTo(tm);
                        if (e.hasAttribute("name")) r.setName(e.getAttribute("name"));
                        if (e.hasAttribute("stereotype")) r.addStereotype(e.getAttribute("stereotype"));
                        line = dm.createConnector(diagram, r, fv, tv, route);
                        break;
                    }
                    case "Include": {
                        IInclude r = factory.createInclude();
                        r.setFrom(fm); r.setTo(tm);
                        line = dm.createConnector(diagram, r, fv, tv, route);
                        break;
                    }
                    case "Extend": {
                        // XML follows UML (extension -> base); VP stores the base as "from".
                        IExtend r = factory.createExtend();
                        if (e.hasAttribute("condition")) r.setCondition(e.getAttribute("condition"));
                        r.setFrom(tm); r.setTo(fm);
                        Point[] reversed = null;
                        if (route != null) {
                            reversed = route.clone();
                            Collections.reverse(Arrays.asList(reversed));
                        }
                        line = dm.createConnector(diagram, r, tv, fv, reversed);
                        // VP adds an "ExtensionPoint" to the base use case; the essay uses none.
                        IExtensionPoint point = r.getExtensionPoint();
                        if (point != null) {
                            r.setExtensionPoint(null);
                            point.delete();
                        }
                        break;
                    }
                    case "ControlFlow": {
                        IControlFlow r = factory.createControlFlow();
                        r.setFrom(fm); r.setTo(tm);
                        if (e.hasAttribute("guard")) r.setGuard(e.getAttribute("guard"));
                        if (swim != null) swim.addChild(r);
                        line = dm.createConnector(diagram, r, fv, tv, route);
                        break;
                    }
                    case "Transition": {
                        IModelElement r = factory.create("Transition2");
                        ((IRelationship) r).setFrom(fm); ((IRelationship) r).setTo(tm);
                        if (e.hasAttribute("name")) r.setName(e.getAttribute("name"));
                        if (e.hasAttribute("guard")) {
                            IConstraintElement guard = factory.createConstraintElement();
                            ICompositeValueSpecification spec = factory.createCompositeValueSpecification();
                            spec.setValue(e.getAttribute("guard"));
                            guard.setSpecification(spec);
                            ((ITransition2) r).setGuard(guard);
                        }
                        line = dm.createConnector(diagram, r, fv, tv, route);
                        break;
                    }
                    case "Message": {
                        IMessage r = factory.createMessage();
                        r.setName(e.hasAttribute("name") ? e.getAttribute("name") : "");
                        r.setFrom(fm); r.setTo(tm);
                        if (yes(e, "return")) r.setActionType(factory.createActionTypeReturn());
                        else if (yes(e, "create")) {
                            r.setActionType(factory.createActionTypeCreate());
                            r.setType(IMessage.TYPE_CREATE_MESSAGE);
                        } else {
                            IActionTypeCall call = factory.createActionTypeCall();
                            call.setAsynchronous(false);
                            r.setActionType(call);
                            r.setAsynchronous(false);
                        }
                        if (yes(e, "self")) r.setType(IMessage.TYPE_SELF_MESSAGE);
                        line = dm.createConnector(diagram, r, fv, tv, route);
                        break;
                    }
                    case "Link": {
                        ILink r = factory.createLink();
                        r.setFrom(fm); r.setTo(tm);
                        if (e.hasAttribute("name")) r.setName(e.getAttribute("name"));
                        line = dm.createConnector(diagram, r, fv, tv, route);
                        break;
                    }
                    case "Anchor": {
                        line = dm.createConnector(diagram, IShapeTypeConstants.SHAPE_TYPE_ANCHOR, fv, tv, route);
                        break;
                    }
                    default: {
                        // Flowchart flow lines and other simple named connectors.
                        IModelElement r = factory.create(type);
                        if (r == null) throw new IllegalStateException("Cannot create " + type);
                        if (r instanceof IRelationship) {
                            ((IRelationship) r).setFrom(fm);
                            ((IRelationship) r).setTo(tm);
                        }
                        if (e.hasAttribute("name")) r.setName(e.getAttribute("name"));
                        line = dm.createConnector(diagram, r, fv, tv, route);
                    }
                }
            } catch (RuntimeException error) {
                throw new IllegalStateException(id + ": edge " + from + " -> " + to + ": " + error.getMessage(), error);
            }
            if (line == null) throw new IllegalStateException(id + ": VP refused edge " + from + " -> " + to);
            font(line);
            // Every label position comes from the XML (absolute diagram coordinates, text centred in the box);
            // VP would otherwise recompute them next to the shapes when the diagram is exported.
            boolean placed = false;
            Rectangle r;
            if (line instanceof IConnectorUIModel && (r = rect(e, "label")) != null) {
                ((IConnectorUIModel) line).getCaptionUIModel().setBounds(r.x, r.y, r.width, r.height);
                labels.add(r);
                placed = true;
            }
            if (line instanceof IAssociationUIModel) {
                // End labels: "A" is the from end, "B" the to end.
                IAssociationUIModel au = (IAssociationUIModel) line;
                if ((r = rect(e, "fromMult")) != null) { au.setHasMultiplicityAShape(true); au.setMultiplicityARectangle(r); labels.add(r); placed = true; }
                if ((r = rect(e, "toMult")) != null) { au.setHasMultiplicityBShape(true); au.setMultiplicityBRectangle(r); labels.add(r); placed = true; }
                if ((r = rect(e, "fromRoleBox")) != null) { au.setHasRoleAShape(true); au.setRoleARectangle(r); labels.add(r); placed = true; }
                if ((r = rect(e, "toRoleBox")) != null) { au.setHasRoleBShape(true); au.setRoleBRectangle(r); labels.add(r); placed = true; }
            }
            if (placed) line.setRequestResetCaption(false);
            // Connectors that share a route with a labelled one keep their stereotype in the model only.
            if ("false".equals(e.getAttribute("caption")) && line instanceof IConnectorUIModel) {
                ((IConnectorUIModel) line).setShowConnectorName(IDiagramUIModel.SHOW_CONNECTOR_NAME_NO);
                ((IConnectorUIModel) line).getCaptionUIModel().setVisible(false);
            }
        }

        void debug() {
            Iterator<?> it = diagram.diagramElementIterator();
            while (it.hasNext()) {
                IDiagramElement element = (IDiagramElement) it.next();
                String name = element.getModelElement() == null ? "" : element.getModelElement().getName();
                StringBuilder sb = new StringBuilder("DEBUG " + id + " " + element.getClass().getSimpleName() + " '" + name
                    + "' bounds=" + element.getX() + "," + element.getY() + "," + element.getWidth() + "," + element.getHeight());
                if (element instanceof IConnectorUIModel) {
                    IConnectorUIModel c = (IConnectorUIModel) element;
                    sb.append(" pts=").append(Arrays.toString(c.getPoints()));
                    ICaptionUIModel cap = c.getCaptionUIModel();
                    if (cap != null) sb.append(" caption=" + cap.getX() + "," + cap.getY() + "," + cap.getWidth() + "," + cap.getHeight());
                    sb.append(" style=" + c.getConnectorStyle());
                }
                if (element instanceof IAssociationUIModel) {
                    IAssociationUIModel a = (IAssociationUIModel) element;
                    sb.append(" multA=" + a.getMultiplicityARectangle() + " hasA=" + a.hasMultiplicityAShape()
                        + " multB=" + a.getMultiplicityBRectangle() + " roleA=" + a.getRoleARectangle()
                        + " roleB=" + a.getRoleBRectangle());
                }
                if (element instanceof IShapeUIModel && ((IShapeUIModel) element).getCaptionUIModel() != null) {
                    ICaptionUIModel cap = ((IShapeUIModel) element).getCaptionUIModel();
                    sb.append(" shapeCaption=" + cap.getX() + "," + cap.getY() + "," + cap.getWidth() + "," + cap.getHeight());
                }
                System.out.println(sb);
                if (element instanceof IConnectorUIModel) {
                    for (IShapeUIModel child : ((IConnectorUIModel) element).toChildArray())
                        System.out.println("DEBUG   child " + child.getClass().getSimpleName() + " type=" + child.getShapeType()
                            + " bounds=" + child.getX() + "," + child.getY() + "," + child.getWidth() + "," + child.getHeight()
                            + " model=" + (child.getModelElement() == null ? null : child.getModelElement().getModelType()));
                }
            }
        }

        Rectangle rect(Element e, String key) {
            if (!e.hasAttribute(key + "X")) return null;
            return new Rectangle(num(e, key + "X", 0), num(e, key + "Y", 0), num(e, key + "W", 40), num(e, key + "H", 20));
        }

        // ----------------------------------------------------------- export

        void export() throws Exception {
            File dir = out;
            dir.mkdirs();
            // The image always ends 2 px around the outermost elements and the Community Edition footer is
            // painted in its bottom-right corner: two empty text boxes widen the image by a margin and a
            // bottom strip for the footer. They are removed again before the project is saved.
            List<IShapeUIModel> spacers = new ArrayList<>();
            if (!(diagram instanceof IERDiagramUIModel)) {
                Rectangle a = exportArea();
                for (Point p : new Point[] {new Point(a.x, a.y), new Point(a.x + a.width - 4, a.y + a.height - 4)}) {
                    IShapeUIModel spacer = (IShapeUIModel) dm.createDiagramElement(diagram, IShapeTypeConstants.SHAPE_TYPE_TEXT_BOX);
                    spacer.setBounds(p.x, p.y, 4, 4);
                    spacer.getLineModel().setTransparency(100, true);
                    spacer.getFillColor().setTransparency(100, true);
                    spacers.add(spacer);
                }
            }
            // PNG at 3x for the slides, SVG for editing, PDF (vector, text kept as text) for the report.
            ExportDiagramAsImageOption png = new ExportDiagramAsImageOption(ExportDiagramAsImageOption.IMAGE_TYPE_PNG);
            png.setScale(3f);
            png.setTextAntiAliasing(true);
            png.setGraphicAntiAliasing(true);
            ModelConvertionManager convert = ApplicationManager.instance().getModelConvertionManager();
            convert.exportDiagramAsImage(diagram, new File(dir, id + ".png"), png, (Rectangle) null);
            ExportDiagramAsImageOption svg = new ExportDiagramAsImageOption(ExportDiagramAsImageOption.IMAGE_TYPE_SVG);
            convert.exportDiagramAsImage(diagram, new File(dir, id + ".svg"), svg, (Rectangle) null);
            ExportDiagramAsImageOption pdf = new ExportDiagramAsImageOption(ExportDiagramAsImageOption.IMAGE_TYPE_PDF);
            pdf.setTextAntiAliasing(true);
            pdf.setGraphicAntiAliasing(true);
            pdf.setImageMargin(ExportDiagramImageMargin.Minimal);
            convert.exportDiagramAsImage(diagram, new File(dir, id + ".pdf"), pdf, (Rectangle) null);
            for (IShapeUIModel spacer : spacers) spacer.deleteViewOnly();
            System.out.println("EXPORTED " + id);
        }

        /** Content bounds plus a bottom strip, so the edition footer never covers a shape. */
        Rectangle exportArea() {
            int[] box = {Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MIN_VALUE, Integer.MIN_VALUE};
            Iterator<?> it = diagram.diagramElementIterator();
            while (it.hasNext()) {
                IDiagramElement element = (IDiagramElement) it.next();
                if (element instanceof IShapeUIModel) {
                    grow(box, element.getX(), element.getY(), element.getWidth(), element.getHeight());
                    IShapeUIModel shape = (IShapeUIModel) element;
                    // Captions drawn outside their shape (actors) use diagram coordinates; inner ones start at 0,0.
                    ICaptionUIModel caption = shape.getCaptionUIModel();
                    if (caption != null && caption.getWidth() > 0 && caption.getHeight() > 0
                            && (caption.getX() != 0 || caption.getY() != 0))
                        grow(box, caption.getX(), caption.getY(), caption.getWidth(), caption.getHeight());
                } else if (element instanceof IConnectorUIModel) {
                    Point[] pts = ((IConnectorUIModel) element).getPoints();
                    if (pts != null) for (Point p : pts) grow(box, p.x, p.y, 1, 1);
                }
            }
            for (Rectangle r : labels) grow(box, r.x, r.y, r.width, r.height);
            int pad = num(spec, "pad", 12), foot = num(spec, "foot", 30);
            return new Rectangle(box[0] - pad, box[1] - pad, box[2] - box[0] + 2 * pad, box[3] - box[1] + pad + foot);
        }

        void grow(int[] box, int x, int y, int w, int h) {
            box[0] = Math.min(box[0], x); box[1] = Math.min(box[1], y);
            box[2] = Math.max(box[2], x + w); box[3] = Math.max(box[3], y + h);
        }
    }
}
