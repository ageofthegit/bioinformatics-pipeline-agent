"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const API = "http://127.0.0.1:8766/api";

type Dataset = {
  accession: string;
  name: string;
  organism: string;
  reads: number;
  size_bytes: number | null;
  path: string;
  kind: string;
  ready: boolean;
};

type Phase = { number: number; title: string; summary: string };
type PriorRun = { run_id: string; status: string; input: string; runner: string };
type Bootstrap = { datasets: Dataset[]; phases: Phase[]; recent_runs: PriorRun[] };
type RunState = {
  output: string;
  awaiting: "resources" | "plan" | "retry" | "report" | null;
  running: boolean;
  exit_code: number | null;
  run_directory: string;
  report: string;
};

function formatBytes(value: number | null) {
  if (value === null) return "Not downloaded";
  if (value < 1000) return `${value} B`;
  if (value < 1_000_000) return `${(value / 1000).toFixed(1)} KB`;
  return `${(value / 1_000_000).toFixed(1)} MB`;
}

function formatReads(value: number) {
  return new Intl.NumberFormat("en-AU").format(value);
}

function gateCopy(gate: RunState["awaiting"]) {
  if (gate === "plan") return ["Plan approval", "Do you approve this analysis plan?"];
  if (gate === "report") return ["Report review", "Have you reviewed and accepted this report?"];
  if (gate === "retry") return ["Retry approval", "Allow one unchanged retry?"];
  return ["Resource approval", "Approve the requested resource increase?"];
}

export default function Home() {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"run" | "roadmap" | "history">("run");
  const [accession, setAccession] = useState("ERR1229325");
  const [runner, setRunner] = useState("python");
  const [executor, setExecutor] = useState("direct");
  const [explanation, setExplanation] = useState("offline-demo");
  const [sessionId, setSessionId] = useState("");
  const [run, setRun] = useState<RunState | null>(null);
  const [showReport, setShowReport] = useState(false);
  const outputRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    fetch(`${API}/bootstrap`)
      .then(async (response) => {
        if (!response.ok) throw new Error("The local workflow bridge is not ready.");
        return response.json();
      })
      .then((data: Bootstrap) => setBootstrap(data))
      .catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const poll = async () => {
      try {
        const response = await fetch(`${API}/runs/${sessionId}`);
        const data = (await response.json()) as RunState & { error?: string };
        if (!response.ok) throw new Error(data.error || "Could not read the run.");
        setRun(data);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Could not read the run.");
      }
    };
    poll();
    const timer = window.setInterval(poll, 650);
    return () => window.clearInterval(timer);
  }, [sessionId]);

  useEffect(() => {
    if (outputRef.current && !showReport) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [run?.output, showReport]);

  const selected = useMemo(
    () => bootstrap?.datasets.find((dataset) => dataset.accession === accession),
    [bootstrap, accession],
  );

  async function startRun() {
    setError("");
    setRun(null);
    setShowReport(false);
    const response = await fetch(`${API}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accession, runner, executor, explanation }),
    });
    const data = (await response.json()) as { session_id?: string; error?: string };
    if (!response.ok || !data.session_id) {
      setError(data.error || "The run could not be started.");
      return;
    }
    setSessionId(data.session_id);
  }

  async function decide(approve: boolean) {
    if (!sessionId) return;
    const response = await fetch(`${API}/runs/${sessionId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approve }),
    });
    const data = (await response.json()) as { error?: string };
    if (!response.ok) setError(data.error || "The decision was not recorded.");
  }

  const status = run?.awaiting
    ? "Decision needed"
    : run?.running
      ? "Running"
      : run
        ? "Finished"
        : "Ready";

  return (
    <main>
      <header className="masthead">
        <a className="brand" href="#top" aria-label="Helix Agent home">
          <span className="brand-mark" aria-hidden="true">H</span>
          <span><b>HELIX</b><small>BIOINFORMATICS AGENT</small></span>
        </a>
        <nav aria-label="Dashboard sections">
          <button className={tab === "run" ? "active" : ""} onClick={() => setTab("run")}>Run lab</button>
          <button className={tab === "roadmap" ? "active" : ""} onClick={() => setTab("roadmap")}>12 phases</button>
          <button className={tab === "history" ? "active" : ""} onClick={() => setTab("history")}>Run history</button>
        </nav>
        <div className="local-status"><i /> LOCAL · HUMAN CONTROLLED</div>
      </header>

      <section className="hero" id="top">
        <div>
          <p className="eyebrow">PHASE 12 · VISUAL WORKSPACE</p>
          <h1>From raw reads<br />to a human decision.</h1>
        </div>
        <p className="hero-copy">
          Choose verified genomic data, inspect the plan, approve each gate and
          read the evidence—all without giving the agent final authority.
        </p>
        <div className={`status-lozenge ${run?.awaiting ? "attention" : ""}`}>
          <span>{status}</span>
          <strong>{selected?.accession || "Loading catalog"}</strong>
        </div>
      </section>

      <section className="phase-rail" aria-label="Project progress">
        {(bootstrap?.phases || []).map((phase) => (
          <button
            key={phase.number}
            className={phase.number < 11 ? "done" : phase.number === 11 ? "current" : "next"}
            onClick={() => setTab("roadmap")}
            title={phase.title}
          >
            <span>{phase.number}</span><i />
          </button>
        ))}
      </section>

      {error && <div className="error-banner"><b>Check needed</b><span>{error}</span></div>}

      {tab === "run" && (
        <section className="workspace">
          <aside className="control-panel">
            <div className="section-heading">
              <span>01</span><div><p>INPUT</p><h2>Choose a sample</h2></div>
            </div>
            <div className="dataset-list">
              {(bootstrap?.datasets || []).map((dataset) => (
                <button
                  key={dataset.accession}
                  className={dataset.accession === accession ? "dataset selected" : "dataset"}
                  onClick={() => setAccession(dataset.accession)}
                  disabled={Boolean(run?.running)}
                >
                  <span className="dataset-radio" />
                  <span className="dataset-main">
                    <b>{dataset.accession}</b><small>{dataset.organism}</small>
                  </span>
                  <span className="dataset-meta">{formatReads(dataset.reads)} reads<br />{formatBytes(dataset.size_bytes)}</span>
                </button>
              ))}
            </div>

            <div className="section-heading configure-heading">
              <span>02</span><div><p>METHOD</p><h2>Configure the run</h2></div>
            </div>
            <div className="field-grid">
              <label>Runner<select value={runner} onChange={(event) => setRunner(event.target.value)} disabled={Boolean(run?.running)}><option value="python">Python reference</option><option value="nextflow">Nextflow pipeline</option></select></label>
              <label>Executor<select value={executor} onChange={(event) => setExecutor(event.target.value)} disabled={Boolean(run?.running)}><option value="direct">Direct</option><option value="local-queue">Local queue</option></select></label>
              <label className="wide">Explanation<select value={explanation} onChange={(event) => setExplanation(event.target.value)} disabled={Boolean(run?.running)}><option value="offline-demo">Offline plain-language guide</option><option value="none">Measurements only</option></select></label>
            </div>
            <div className="safety-note"><span>HUMAN GATES</span><p>The dashboard cannot auto-approve a plan, retry or report.</p></div>
            <button className="start-button" onClick={startRun} disabled={!bootstrap || Boolean(run?.running)}>
              <span>{run?.running ? "Workflow in progress" : "Prepare analysis plan"}</span><b>→</b>
            </button>
          </aside>

          <section className="run-panel">
            <div className="run-head">
              <div><p>LIVE WORKFLOW</p><h2>{selected?.organism || "Waiting for the local bridge"}</h2></div>
              <span className={`run-state ${run?.awaiting ? "attention" : ""}`}><i />{status}</span>
            </div>

            {run?.awaiting && (
              <div className="approval-card">
                <div className="approval-number">03</div>
                <div><p>{gateCopy(run.awaiting)[0]}</p><h3>{gateCopy(run.awaiting)[1]}</h3><small>Your choice is written to the audit history.</small></div>
                <div className="approval-actions"><button className="reject" onClick={() => decide(false)}>No, stop here</button><button className="approve" onClick={() => decide(true)}>Yes, approve</button></div>
              </div>
            )}

            <div className="evidence-tabs">
              <button className={!showReport ? "active" : ""} onClick={() => setShowReport(false)}>Live trace</button>
              <button className={showReport ? "active" : ""} onClick={() => setShowReport(true)} disabled={!run?.report}>Human report</button>
              {run?.run_directory && <span>{run.run_directory.split("/").pop()}</span>}
            </div>
            {!run ? (
              <div className="empty-state">
                <div className="sequence-mark">ACGT<span>••</span>TGCA</div>
                <h3>No analysis running</h3>
                <p>Select a sample and prepare its plan. Nothing executes until you approve it.</p>
              </div>
            ) : showReport && run.report ? (
              <pre className="report-view">{run.report}</pre>
            ) : (
              <pre className="trace-view" ref={outputRef}>{run.output}</pre>
            )}
          </section>
        </section>
      )}

      {tab === "roadmap" && (
        <section className="roadmap-view">
          <div className="roadmap-intro"><p className="eyebrow">THE COMPLETE BUILD</p><h2>Twelve small phases.<br />One controlled workflow.</h2><p>Each phase added one capability while keeping decisions with a person.</p></div>
          <div className="phase-grid">
            {(bootstrap?.phases || []).map((phase) => (
              <article key={phase.number} className={phase.number < 11 ? "complete" : phase.number === 11 ? "current" : "up-next"}>
                <div><span>{String(phase.number).padStart(2, "0")}</span><i /></div><p>{phase.number < 11 ? "COMPLETE" : phase.number === 11 ? "IN REVIEW" : "BUILDING"}</p><h3>{phase.title}</h3><small>{phase.summary}</small>
              </article>
            ))}
          </div>
        </section>
      )}

      {tab === "history" && (
        <section className="history-view">
          <div className="roadmap-intro"><p className="eyebrow">AUDITABLE BY DEFAULT</p><h2>Recent decisions<br />and evidence.</h2><p>Every run has state, audit events and—after Phase 10—a reproducibility manifest.</p></div>
          <div className="history-table">
            <div className="history-row header"><span>Run</span><span>Input</span><span>Runner</span><span>Final state</span></div>
            {(bootstrap?.recent_runs || []).map((item) => <div className="history-row" key={item.run_id}><b>{item.run_id}</b><span>{item.input}</span><span>{item.runner}</span><em className={item.status.includes("accepted") ? "accepted" : "review"}>{item.status.replaceAll("_", " ")}</em></div>)}
          </div>
        </section>
      )}

      <footer><span>LOCAL RESEARCH WORKSPACE · NO CLINICAL INTERPRETATION</span><span>AGENT RECOMMENDS → HUMAN APPROVES → AGENT ACTS → HUMAN REVIEWS</span></footer>
    </main>
  );
}
