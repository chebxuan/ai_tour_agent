"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { demoJourneys } from "@/data/demoJourneys";
import { createDemoPreview } from "@/lib/demoPreview";
import TripForm from "./TripForm";
import ItineraryPreview from "./ItineraryPreview";
import styles from "./Planner.module.css";

function PlannerWorkspace({ initialJourney }) {
  const [form, setForm] = useState({ city: initialJourney?.city || "", days: String(initialJourney?.days || 3), date: "", adults: "2", children: "0", seniors: "0", interests: ["文化探索", "轻松慢游"], guide: true, car: false, notes: "" });
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const dirty = !!result && JSON.stringify(result.request) !== JSON.stringify(form);
  const preferredJourney = initialJourney?.city === form.city && initialJourney?.days === Number(form.days) ? initialJourney : null;

  async function generate(event) {
    event.preventDefault();
    if (status === "loading") return;
    setStatus("loading");
    setError("");
    try {
      const preview = await createDemoPreview(form, preferredJourney?.id);
      setResult(preview);
      setStatus(preview ? "success" : "empty");
    } catch {
      setStatus("error");
      setError("请稍后重试，或调整你的需求。");
    }
  }
  return <div className={styles.workspace}><TripForm form={form} onChange={setForm} onSubmit={generate} busy={status === "loading"} preferredJourney={preferredJourney} /><ItineraryPreview result={result} status={status} dirty={dirty} error={error} /></div>;
}

export default function TravelPlanner() {
  const searchParams = useSearchParams();
  const initialJourney = demoJourneys.find((journey) => journey.id === searchParams.get("journey"));
  return <PlannerWorkspace key={initialJourney?.id || "custom"} initialJourney={initialJourney} />;
}
