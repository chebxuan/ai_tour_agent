"use client";
import { useState } from "react";
import { demoJourneys, demoCities } from "@/data/demoJourneys";
import ProductCard from "./ProductCard";
import Icon from "./Icon";
import styles from "./Home.module.css";

export default function JourneyCatalog() {
  const [city, setCity] = useState("全部");
  const [duration, setDuration] = useState("all");
  const journeys = demoJourneys.filter((journey) => (city === "全部" || journey.city === city) && (duration === "all" || journey.days === Number(duration)));
  return <section className={styles.catalog} id="destinations" aria-labelledby="journeys-title">
    <div className={styles.sectionHeading} id="journeys"><div><p className="eyebrow">FIND YOUR NEXT CHAPTER</p><h2 id="journeys-title" className="section-title">从一座城市，开启一段旅程。</h2></div><p className="section-copy">不必急着决定一切。<br />先找一条让你心动的路线。</p></div>
    <div className={styles.filters}>
      <div className={styles.cityFilters} role="group" aria-label="按目的地筛选">{["全部", ...demoCities].map((name) => <button key={name} type="button" aria-pressed={city === name} className={city === name ? styles.filterActive : ""} onClick={() => setCity(name)}>{name}</button>)}</div>
      <label className={styles.durationFilter}><Icon name="calendar" size={18} /><span>天数</span><select aria-label="按行程天数筛选" value={duration} onChange={(event) => setDuration(event.target.value)}><option value="all">不限</option><option value="2">2 天</option><option value="3">3 天</option></select></label>
    </div>
    <p className={styles.catalogNote} aria-live="polite">共 {journeys.length} 条展示样例 · 正式产品内容将在下一轮补充</p>
    {journeys.length ? <div className={styles.productGrid}>{journeys.map((journey) => <ProductCard key={journey.id} journey={journey} />)}</div> : <div className={styles.noResults}><Icon name="compass" size={36} /><h3>换一个选择，看看更多风景。</h3><p>当前没有符合这一组合的展示样例。</p><button type="button" className="button button--secondary" onClick={() => { setCity("全部"); setDuration("all"); }}>清除筛选</button></div>}
  </section>;
}
