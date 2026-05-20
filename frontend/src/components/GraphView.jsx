import { useEffect, useMemo, useState } from "react";
import * as N3 from "n3";
import * as Reactodia from "@reactodia/workspace";

const { namedNode, literal, quad } = N3.DataFactory;
const APP_BASE_PATH = (window.__APP_BASE_PATH__ || "").trim().replace(/\/+$/, "");

function resolveLayoutWorkerUrl() {
  const workerUrl = new URL("@reactodia/workspace/layout.worker", import.meta.url);
  if (APP_BASE_PATH && workerUrl.pathname.startsWith("/assets/")) {
    workerUrl.pathname = `${APP_BASE_PATH}${workerUrl.pathname}`;
  }
  return workerUrl;
}

const Layouts = Reactodia.defineLayoutWorker(
  () => new Worker(resolveLayoutWorkerUrl())
);

const ALLOWED_TYPES = new Set([
  "https://admin-shell.io/aas/3/AssetAdministrationShell",
  "https://admin-shell.io/aas/3/Submodel",
  "https://admin-shell.io/aas/3/Environment",
]);

function iriLocalPart(iri) {
  const hashIndex = iri.lastIndexOf("#");
  if (hashIndex >= 0 && hashIndex < iri.length - 1) {
    return iri.slice(hashIndex + 1);
  }
  const slashIndex = iri.lastIndexOf("/");
  if (slashIndex >= 0 && slashIndex < iri.length - 1) {
    return iri.slice(slashIndex + 1);
  }
  return iri;
}

function collectLiteralValuesFromTerm(term, quads, visited = new Set()) {
  if (term.termType === "Literal") {
    return term.value ? [term.value] : [];
  }
  if (term.termType !== "BlankNode") {
    return [];
  }
  if (visited.has(term.value)) {
    return [];
  }
  visited.add(term.value);

  const values = [];
  for (const item of quads) {
    if (item.subject.termType === "BlankNode" && item.subject.value === term.value) {
      values.push(...collectLiteralValuesFromTerm(item.object, quads, visited));
    }
  }
  return values;
}

function firstLiteralValueFor(subjectIri, quads, localName) {
  for (const item of quads) {
    if (item.subject.termType !== "NamedNode" || item.subject.value !== subjectIri) {
      continue;
    }
    const predicateLocal = Reactodia.Rdf.getLocalName(item.predicate.value) ?? item.predicate.value;
    if (predicateLocal !== localName) {
      continue;
    }
    const values = collectLiteralValuesFromTerm(item.object, quads);
    if (values.length > 0) {
      return values[0];
    }
  }
  return undefined;
}

function buildSeedGraph(quads) {
  const seedIds = new Set();

  for (const quad of quads) {
    if (
      quad.predicate.termType === "NamedNode" &&
      quad.predicate.value === "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" &&
      quad.object.termType === "NamedNode" &&
      ALLOWED_TYPES.has(quad.object.value) &&
      quad.subject.termType === "NamedNode"
    ) {
      seedIds.add(quad.subject.value);
    }
  }

  const enrichedQuads = [...quads];

  const labelPredicate = namedNode("http://www.w3.org/2000/01/rdf-schema#label");
  for (const seedId of seedIds) {
    const displayName = firstLiteralValueFor(seedId, quads, "displayName");
    const idShort = firstLiteralValueFor(seedId, quads, "idShort");
    const idValue = firstLiteralValueFor(seedId, quads, "id");
    const labelValue = displayName || idShort || idValue || iriLocalPart(seedId);
    enrichedQuads.push(quad(namedNode(seedId), labelPredicate, literal(labelValue)));
  }

  return { seedIds, enrichedQuads };
}

export default function GraphView({ turtle }) {
  const [layoutMode, setLayoutMode] = useState("default");
  const [layoutWarning, setLayoutWarning] = useState("");
  const { defaultLayout, forceLayout, flowLayout } = Reactodia.useWorker(Layouts);

  useEffect(() => {
    setLayoutWarning("");
  }, [turtle, layoutMode]);

  const selectedLayout = useMemo(() => {
    if (layoutMode === "force") {
      return forceLayout;
    }
    if (layoutMode === "flow") {
      return flowLayout;
    }
    return defaultLayout;
  }, [layoutMode, defaultLayout, forceLayout, flowLayout]);

  const parsed = useMemo(() => {
    if (!turtle.trim()) {
      return null;
    }

    try {
      const quads = new N3.Parser().parse(turtle);
      return { quads, error: null };
    } catch (error) {
      return { quads: null, error: String(error) };
    }
  }, [turtle]);

  const { onMount } = Reactodia.useLoadedWorkspace(async ({ context, signal }) => {
    if (!parsed || parsed.error || !parsed.quads) {
      return;
    }

    const { model, performLayout } = context;
    const { seedIds, enrichedQuads } = buildSeedGraph(parsed.quads);
    const dataProvider = new Reactodia.RdfDataProvider({ acceptBlankNodes: false });
    dataProvider.addGraph(enrichedQuads);

    await model.createNewDiagram({ dataProvider, signal });

    for (const id of seedIds) {
      model.createElement(id);
    }

    await model.requestData();
    try {
      await performLayout({ signal, layoutFunction: selectedLayout });
    } catch (error) {
      console.error("Failed to compute graph layout", error);
      setLayoutWarning("Layout worker failed in this deployment. Graph rendering continues without auto-layout.");
    }
  }, [parsed, selectedLayout]);

  let content = <div className="graph-placeholder">Convert JSON to RDF to visualize it here.</div>;
  if (parsed?.error) {
    content = <div className="graph-placeholder">Unable to parse RDF Turtle: {parsed.error}</div>;
  } else if (parsed?.quads) {
    content = (
      <Reactodia.Workspace key={layoutMode} ref={onMount} defaultLayout={selectedLayout}>
        <Reactodia.DefaultWorkspace />
      </Reactodia.Workspace>
    );
  }

  return (
    <div className="graph-shell">
      <div className="graph-layout-picker-wrap">
        <label className="graph-layout-label" htmlFor="graph-layout-picker">Layout</label>
        <select
          id="graph-layout-picker"
          className="graph-layout-picker"
          value={layoutMode}
          onChange={(e) => setLayoutMode(e.target.value)}
          disabled={!parsed || Boolean(parsed.error)}
        >
          <option value="default">Default (balanced)</option>
          <option value="force">Force-directed</option>
          <option value="flow">Flow (hierarchical)</option>
        </select>
      </div>
      {layoutWarning && (
        <div className="graph-layout-warning">{layoutWarning}</div>
      )}
      <div className="graph-host">
        {content}
      </div>
    </div>
  );
}
