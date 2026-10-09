import { Suspense } from "react";
import Link from "next/link";
import TravelPlanner from "@/components/TravelPlanner";
import Icon from "@/components/Icon";
import styles from "@/components/Planner.module.css";

export const metadata = { title: "Design Your Journey" };

export default function PlanPage() {
  return <main id="main" className={`container ${styles.planPage}`}><Link href="/#journeys" className={styles.backLink}><Icon size={16} />Back to destinations</Link><div className={styles.pageHeading}><div><p className="eyebrow">DESIGNED AROUND YOU</p><h1>Design your journey through China.</h1><p>Choose a destination. Discover the stories and experiences that could shape your days.</p></div><span className={styles.demoBadge}><span />Your journey preview</span></div><Suspense fallback={<div className={styles.routeLoading}>Opening your journey planner…</div>}><TravelPlanner /></Suspense></main>;
}
