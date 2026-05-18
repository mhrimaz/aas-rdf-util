import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  IconButton,
  InputAdornment,
  Link,
  Stack,
  Tab,
  Tabs,
  TextField,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import HubIcon from "@mui/icons-material/Hub";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import { instance as createVizInstance } from "@viz-js/viz";
import GraphView from "./components/GraphView";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const AASQL_PATH = "/aasql";
const FAQ_PATH = "/faq";
const HOME_PATH = "/";
const SWAGGER_URL = "/docs";
const LINKEDIN_URL = "https://www.linkedin.com/in/mhrimaz/";
const REACTODIA_URL = "https://reactodia.github.io/";
const METAPHACTS_URL = "https://metaphacts.com/";
const PY_AAS_RDF_URL = "https://github.com/mhrimaz/py-aas-rdf";
const DOCKERHUB_LOCAL_SETUP = "docker run --rm -p 8000:8000 mhrimaz/aas-rdf-util:latest";
const FAQ_INDEX_PATH = "/faq-index.json";

async function postJson(path, body) {
  const payload = await postJsonPayload(path, body);
  return payload.output;
}

async function postJsonPayload(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Request failed with status ${response.status}`);
  }
  return payload;
}

function navigate(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

async function copyToClipboard(text) {
  await navigator.clipboard.writeText(text ?? "");
}

function getCurrentPage() {
  if (window.location.pathname.startsWith(FAQ_PATH)) return "faq";
  if (window.location.pathname.startsWith(AASQL_PATH)) return "aasql";
  return "home";
}

function useScrollState() {
  const [scrolled, setScrolled] = useState(window.scrollY > 4);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 4);
    const handlePopState = () => setScrolled(window.scrollY > 4);
    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("popstate", handlePopState);
    handleScroll();
    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  return scrolled;
}

function PageShell({ title, activePage, scrolled }) {
  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        backdropFilter: scrolled ? "blur(16px)" : "none",
        backgroundColor: scrolled ? "rgba(247, 248, 244, 0.94)" : "transparent",
        borderBottom: scrolled ? "1px solid rgba(15, 23, 42, 0.08)" : "1px solid transparent",
        transition: "background-color 180ms ease, border-color 180ms ease, box-shadow 180ms ease",
        boxShadow: scrolled ? "0 10px 30px rgba(15, 23, 42, 0.08)" : "none",
      }}
    >
      <Toolbar sx={{ py: 1, px: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ flexGrow: 1 }}>
          <HubIcon color="primary" />
          <Typography variant="h5" sx={{ fontWeight: 800, color: "#000" }}>
            AAS &amp; Knowledge Graphs - Tools
          </Typography>
        </Stack>
        <Stack direction="row" spacing={1}>
          <Button
            variant={activePage === "home" ? "contained" : "text"}
            onClick={() => navigate(HOME_PATH)}
          >
            Convert &amp; Visualize
          </Button>
          <Button
            variant={activePage === "aasql" ? "contained" : "text"}
            onClick={() => navigate(AASQL_PATH)}
          >
            AASQL to SPARQL
          </Button>
          <Button
            variant={activePage === "faq" ? "contained" : "text"}
            onClick={() => navigate(FAQ_PATH)}
          >
            FAQ
          </Button>
        </Stack>
      </Toolbar>
      <Box sx={{ px: 3, pb: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {title}
        </Typography>
      </Box>
    </AppBar>
  );
}

function SectionCard({ title, action, children }) {
  return (
    <Card className="panel-card">
      <CardContent>
        <Stack spacing={1.5}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2}>
            <Typography variant="h6">{title}</Typography>
            {action}
          </Stack>
          {children}
        </Stack>
      </CardContent>
    </Card>
  );
}

function EditableField(props) {
  return (
    <TextField
      fullWidth
      multiline
      minRows={props.minRows ?? 10}
      maxRows={props.maxRows ?? 24}
      value={props.value}
      onChange={props.onChange}
      label={props.label}
      className="mono"
      placeholder={props.placeholder}
      InputProps={props.InputProps}
    />
  );
}

function OutputField({ label, value, onChange, minRows = 10 }) {
  return (
    <Stack spacing={1}>
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Typography variant="subtitle2" color="text.secondary">
          {label}
        </Typography>
        <Tooltip title="Copy to clipboard">
          <IconButton aria-label={`Copy ${label}`} onClick={() => copyToClipboard(value)} size="small">
            <ContentCopyIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
      <TextField
        fullWidth
        multiline
        minRows={minRows}
        maxRows={28}
        value={value}
        onChange={onChange}
        className="mono"
        InputProps={{ readOnly: true }}
      />
    </Stack>
  );
}

function Footer() {
  return (
    <Box component="footer" className="site-footer">
      <Container maxWidth={false} sx={{ px: { xs: 2, md: 3 } }}>
        <Stack spacing={1.25} sx={{ py: 3 }} alignItems="center" textAlign="center">
          <Typography variant="body2" color="text.secondary" textAlign="center">
            Don&apos;t know how to unleash the power of RDF, knowledge graph, and semantic technologies?
            {" "}
            Checkout
            {" "}
            <Link href={METAPHACTS_URL} target="_blank" rel="noreferrer">
              metaphacts
            </Link>
            {" "}
            and their enterprise knowledge graph platform.
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center">
            Disclaimer: The services provided on this website are offered &quot;as is&quot; and without any guarantees.
            We do not make any warranties, express or implied, regarding the accuracy, reliability, or suitability
            of the content for any particular purpose. By using this site, you agree to do so at your own risk.
            Diagrams are provided via
            {" "}
            <Link href={REACTODIA_URL} target="_blank" rel="noreferrer">
              Reactodia
            </Link>
            {" "}
            and RDF version provided by
            {" "}
            <Link href={PY_AAS_RDF_URL} target="_blank" rel="noreferrer">
              py-aas-rdf
            </Link>
            .
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} justifyContent="center" alignItems="center">
            <Typography variant="body2" color="text.secondary" textAlign="center">
              Built with 💖 by GPT Codex &amp;
              {" "}
              <Link href={LINKEDIN_URL} target="_blank" rel="noreferrer">
                Hossein Rimaz
              </Link>
            </Typography>
            <Stack direction="row" spacing={2} flexWrap="wrap" justifyContent="center" alignItems="center">
              <Link href={SWAGGER_URL} target="_blank" rel="noreferrer">
                Swagger UI
              </Link>
              <Link href={`https://hub.docker.com/r/mhrimaz/aas-rdf-util`} target="_blank" rel="noreferrer">
                DockerHub
              </Link>
            </Stack>
          </Stack>
          <Box className="footer-command" sx={{ width: "100%", maxWidth: 900 }}>
            <Typography variant="caption" component="div" color="text.secondary">
              One-line local setup from DockerHub
            </Typography>
            <TextField
              fullWidth
              value={DOCKERHUB_LOCAL_SETUP}
              className="mono"
              size="small"
              sx={{ mt: 0.75, backgroundColor: "#fff" }}
              InputProps={{
                readOnly: true,
                endAdornment: (
                  <InputAdornment position="end">
                    <Tooltip title="Copy command">
                      <IconButton
                        aria-label="Copy DockerHub command"
                        onClick={() => copyToClipboard(DOCKERHUB_LOCAL_SETUP)}
                        edge="end"
                        size="small"
                      >
                        <ContentCopyIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </InputAdornment>
                ),
              }}
            />
          </Box>
        </Stack>
      </Container>
    </Box>
  );
}

function detectInputFormat(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return "json";
  }

  const startsLikeJson = trimmed.startsWith("{") || trimmed.startsWith("[");
  if (startsLikeJson) {
    try {
      JSON.parse(trimmed);
      return "json";
    } catch {
      // Fall through to RDF heuristics.
    }
  }

  const rdfHints = [
    "@prefix",
    "PREFIX ",
    "prefix ",
    "<http://",
    "<https://",
    "^^",
    " a ",
    " ;",
    " .",
  ];
  if (rdfHints.some((hint) => trimmed.includes(hint))) {
    return "rdf";
  }

  try {
    JSON.parse(trimmed);
    return "json";
  } catch {
    return "rdf";
  }
}

function HomePage({ scrolled }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sourceText, setSourceText] = useState('{\n  "modelType": "Environment"\n}');
  const [resultText, setResultText] = useState("");
  const [resultKind, setResultKind] = useState("");

  const inputKind = useMemo(() => detectInputFormat(sourceText), [sourceText]);
  const targetKind = inputKind === "json" ? "rdf" : "json";
  const inputLabel = inputKind === "json" ? "AAS JSON input (auto-detected)" : "RDF Turtle input (auto-detected)";
  const outputLabel = inputKind === "json" ? "RDF Turtle output" : "AAS JSON output";
  const convertButtonLabel = inputKind === "json" ? "Convert JSON to RDF" : "Convert RDF to JSON";
  const shownOutput = resultKind === targetKind ? resultText : "";
  const graphTurtle = inputKind === "rdf" ? sourceText : (resultKind === "rdf" ? resultText : "");

  const runAutoConvert = async () => {
    setLoading(true);
    setError("");
    try {
      if (inputKind === "json") {
        const parsed = JSON.parse(sourceText);
        const output = await postJson("/api/convert/json-to-rdf", { data: parsed });
        setResultText(output);
        setResultKind("rdf");
      } else {
        const output = await postJson("/api/convert/rdf-to-json", { turtle: sourceText });
        setResultText(output);
        setResultKind("json");
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageShell
        title="Convert AAS JSON to RDF and render it in a knowledge graph canvas."
        activePage="home"
        scrolled={scrolled}
      />
      <Container maxWidth={false} sx={{ px: { xs: 2, md: 3 }, pb: 4, width: "100%" }}>
        <Stack spacing={2.5} sx={{ width: "100%" }}>
          <SectionCard
            title="AAS JSON ⇄ RDF"
            action={<Chip label={`Detected: ${inputKind.toUpperCase()}`} size="small" />}
          >
            <EditableField
              label={inputLabel}
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              minRows={10}
            />

            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                onClick={runAutoConvert}
                startIcon={<AutorenewIcon />}
              >
                {convertButtonLabel}
              </Button>
            </Stack>

            <OutputField
              label={outputLabel}
              value={shownOutput}
              onChange={() => {}}
              minRows={12}
            />
          </SectionCard>

          <SectionCard title="RDF Visualization">
            <GraphView turtle={graphTurtle} />
          </SectionCard>
        </Stack>

        {loading && (
          <Stack className="loading-overlay" alignItems="center" justifyContent="center">
            <CircularProgress />
          </Stack>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Container>
      <Footer />
    </>
  );
}

function AasqlPage({ scrolled }) {
  const [tab, setTab] = useState(0);
  const [outputTab, setOutputTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [aasqlText, setAasqlText] = useState('$match(\n  $aas#id $eq "https://example.com/asset-administration-shell-1"\n)');
  const [aasqlJson, setAasqlJson] = useState('{\n  "$condition": {\n    "$eq": [\n      {"$field": "$aas#id"},\n      {"$strVal": "https://example.com/asset-administration-shell-1"}\n    ]\n  }\n}');
  const [sparql, setSparql] = useState("");
  const [treeText, setTreeText] = useState("");
  const [treeDot, setTreeDot] = useState("");
  const [treeSvg, setTreeSvg] = useState("");
  const [treeRenderError, setTreeRenderError] = useState("");

  useEffect(() => {
    let active = true;

    async function renderTree() {
      if (!treeDot) {
        setTreeSvg("");
        setTreeRenderError("");
        return;
      }

      try {
        setTreeRenderError("");
        const viz = await createVizInstance();
        const svg = viz.renderString(treeDot, { format: "svg", engine: "dot" });
        if (active) {
          setTreeSvg(svg);
        }
      } catch (err) {
        if (active) {
          setTreeSvg("");
          setTreeRenderError(String(err));
        }
      }
    }

    renderTree();
    return () => {
      active = false;
    };
  }, [treeDot]);

  const currentMode = useMemo(() => (tab === 1 ? "AASQL JSON" : "AASQL text"), [tab]);

  const runAasqlToSparql = async () => {
    setLoading(true);
    setError("");
    try {
      if (tab === 1) {
        const parsed = JSON.parse(aasqlJson);
        const output = await postJson("/api/query/aasql-to-sparql", { query_json: parsed });
        setSparql(output);
        setTreeText("");
        setTreeDot("");
        setTreeSvg("");
        setTreeRenderError("");
      } else {
        const output = await postJson("/api/query/aasql-to-sparql", { query: aasqlText });
        setSparql(output);

        try {
          const treePayload = await postJsonPayload("/api/query/aasql-parse-tree", { query: aasqlText });
          setTreeText(treePayload.tree_text || "");
          setTreeDot(treePayload.tree_dot || "");
        } catch (treeErr) {
          setTreeText("");
          setTreeDot("");
          setTreeSvg("");
          setTreeRenderError(String(treeErr));
        }
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageShell title="Convert AASQL into SPARQL" activePage="aasql" scrolled={scrolled} />
      <Container maxWidth={false} sx={{ px: { xs: 2, md: 3 }, pb: 4, width: "100%" }}>
        <Stack spacing={2.5} sx={{ width: "100%" }}>
          <SectionCard title="AASQL → SPARQL" action={<Chip label={currentMode} size="small" />}>
            <Tabs
              value={tab}
              onChange={(_, value) => {
                setTab(value);
                setOutputTab(0);
              }}
            >
              <Tab label="AASQL text" />
              <Tab label="AASQL JSON" />
            </Tabs>

            {tab === 0 ? (
              <EditableField
                label="AASQL text"
                value={aasqlText}
                onChange={(e) => setAasqlText(e.target.value)}
                minRows={12}
              />
            ) : (
              <EditableField
                label="AASQL JSON"
                value={aasqlJson}
                onChange={(e) => setAasqlJson(e.target.value)}
                minRows={12}
              />
            )}

            <Stack direction="row" spacing={1}>
              <Button variant="contained" onClick={runAasqlToSparql} startIcon={<AutoFixHighIcon />}>
                Convert to SPARQL
              </Button>
            </Stack>

            {tab === 0 ? (
              <>
                <Tabs value={outputTab} onChange={(_, value) => setOutputTab(value)}>
                  <Tab label="SPARQL" />
                  <Tab label="Parse tree" />
                </Tabs>

                {outputTab === 0 ? (
                  <OutputField label="SPARQL" value={sparql} onChange={(e) => setSparql(e.target.value)} minRows={14} />
                ) : (
                  <Stack spacing={1.5}>
                    <Stack spacing={1}>
                      <Typography variant="subtitle2" color="text.secondary">
                        Parse tree visualization
                      </Typography>
                      {treeSvg ? (
                        <Box
                          sx={{
                            border: "1px solid rgba(15, 23, 42, 0.12)",
                            borderRadius: 1,
                            p: 1,
                            backgroundColor: "#fff",
                            overflow: "hidden",
                            "& svg": {
                              display: "block",
                              width: "100%",
                              maxWidth: "100%",
                              height: "auto",
                            },
                          }}
                          dangerouslySetInnerHTML={{ __html: treeSvg }}
                        />
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          {treeRenderError
                            ? `Unable to render parse tree diagram: ${treeRenderError}`
                            : "Run conversion in AASQL text mode to generate a parse tree diagram."}
                        </Typography>
                      )}
                    </Stack>

                    <OutputField label="Parse tree (text)" value={treeText} onChange={() => {}} minRows={12} />
                    <OutputField label="Parse tree (DOT)" value={treeDot} onChange={() => {}} minRows={10} />
                  </Stack>
                )}
              </>
            ) : (
              <OutputField label="SPARQL" value={sparql} onChange={(e) => setSparql(e.target.value)} minRows={14} />
            )}
          </SectionCard>
        </Stack>

        {loading && (
          <Stack className="loading-overlay" alignItems="center" justifyContent="center">
            <CircularProgress />
          </Stack>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Container>
      <Footer />
    </>
  );
}

function FaqPage({ scrolled }) {
  const [faqEntries, setFaqEntries] = useState([]);
  const [faqError, setFaqError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadFaq() {
      setFaqError("");
      try {
        const response = await fetch(FAQ_INDEX_PATH, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Failed to load FAQ index: ${response.status}`);
        }
        const payload = await response.json();
        const entries = Array.isArray(payload.entries) ? payload.entries : [];
        if (active) {
          setFaqEntries(entries);
        }
      } catch (err) {
        if (active) {
          setFaqError(String(err));
          setFaqEntries([]);
        }
      }
    }

    loadFaq();
    return () => {
      active = false;
    };
  }, []);

  const faqJsonLd = useMemo(
    () => ({
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: faqEntries.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: {
          "@type": "Answer",
          text: item.answer,
        },
      })),
    }),
    [faqEntries]
  );

  return (
    <>
      <PageShell title="Frequently Asked Questions" activePage="faq" scrolled={scrolled} />
      <Box component="script" type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }} />
      <Container maxWidth={false} sx={{ px: { xs: 2, md: 3 }, pb: 4, width: "100%" }}>
        {faqError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {faqError}
          </Alert>
        )}
        <Stack spacing={2.5} sx={{ width: "100%" }}>
          <SectionCard title="Questions & Answers">
            <Stack spacing={1.5}>
              {faqEntries.map((item) => (
                <Card key={item.question} variant="outlined">
                  <CardContent>
                    <Stack spacing={1}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                        {item.question}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {item.answer}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              ))}
              {faqEntries.length === 0 && !faqError && (
                <Typography variant="body2" color="text.secondary">
                  FAQ content is currently unavailable.
                </Typography>
              )}
            </Stack>
          </SectionCard>
        </Stack>
      </Container>
      <Footer />
    </>
  );
}

export default function App() {
  const [path, setPath] = useState(window.location.pathname);
  const scrolled = useScrollState();

  useEffect(() => {
    const update = () => setPath(window.location.pathname);
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);

  const page = getCurrentPage();
  if (page === "aasql" || path.startsWith(AASQL_PATH)) {
    return <AasqlPage scrolled={scrolled} />;
  }
  if (page === "faq" || path.startsWith(FAQ_PATH)) {
    return <FaqPage scrolled={scrolled} />;
  }
  return <HomePage scrolled={scrolled} />;
}
