"use client";

import { useState } from "react";
import TopBar from "@/components/TopBar";
import LeftNav from "@/components/LeftNav";
import PipelineView from "@/components/PipelineView";
import HumanGateCard from "@/components/HumanGateCard";
import EvidenceTable from "@/components/EvidenceTable";
import ModelCard from "@/components/ModelCard";
import SimulationCard from "@/components/SimulationCard";
import RightPanel from "@/components/RightPanel";
import { useResearchStream } from "@/hooks/useResearchStream";

export default function Home() {
  const [activeNav, setActiveNav] = useState("new-research");
  const [question, setQuestion] = useState(
    "Is the topological charge of a spatiotemporal vortex preserved under free-space propagation?"
  );
  const { state, gate, start, resume, connected, isLoading } = useResearchStream();

  return (
    <div className="app">
      <TopBar campaignId={state?.campaign_id} connected={connected} />
      <div className="layout">
        <LeftNav active={activeNav} onSelect={setActiveNav} />
        <main className="center">
          <section className="card">
            <h2>Research Question</h2>
            <textarea
              className="input question-input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <button
              className="btn btn-approve"
              disabled={!connected}
              onClick={() => start(question)}
            >
              Create Research Campaign
            </button>
            {!connected && (
              <p className="gate-note">
                Set <code>NEXT_PUBLIC_GATEWAY_URL</code> to connect the
                gateway (see web/.env.example). The pipeline then runs on the
                LangGraph agent server.
              </p>
            )}
          </section>

          {gate && <HumanGateCard gate={gate} busy={isLoading} onResume={resume} />}

          <section className="card">
            <h2>Pipeline Graph</h2>
            <PipelineView
              status={state?.pipeline_status}
              currentStage={state?.current_stage}
            />
          </section>

          <EvidenceTable items={[]} />

          <ModelCard model={null} />

          <SimulationCard runs={[]} />
        </main>
        <RightPanel state={state} />
      </div>
    </div>
  );
}
