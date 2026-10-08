import { Suspense } from "react";
import Link from "next/link";
import TravelPlanner from "@/components/TravelPlanner";
import Icon from "@/components/Icon";
import styles from "@/components/Planner.module.css";

export const metadata = { title: "定制你的旅程" };

export default function PlanPage() {
  return <main id="main" className={`container ${styles.planPage}`}><Link href="/#journeys" className={styles.backLink}><Icon size={16} />返回探索行程</Link><div className={styles.pageHeading}><div><p className="eyebrow">DESIGNED AROUND YOU</p><h1>设计你的中国旅程。</h1><p>选择你想去的地方，剩下的灵感，在这里慢慢展开。</p></div><span className={styles.demoBadge}><span />交互预览版本</span></div><Suspense fallback={<div className={styles.routeLoading}>正在打开你的旅程规划页…</div>}><TravelPlanner /></Suspense></main>;
}
