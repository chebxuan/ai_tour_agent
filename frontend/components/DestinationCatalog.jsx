"use client";
import { useState } from "react";
import { destinations, destinationThemes } from "@/data/destinations";
import DestinationCard from "./DestinationCard";
import styles from "./Home.module.css";

export default function DestinationCatalog() {
  const [theme, setTheme] = useState("全部目的地");
  const visibleDestinations = destinations.filter((destination) => theme === "全部目的地" || destination.themes.includes(theme));
  return <section className={styles.catalog} id="destinations" aria-labelledby="destinations-title">
    <div className={styles.sectionHeading} id="journeys"><div><p className="eyebrow">PLACES WITH A STORY</p><h2 id="destinations-title" className="section-title">每个地方，都有自己的故事。</h2></div><p className="section-copy">从一座城的日常，<br />走进一个地方的文化。</p></div>
    <div className={styles.cityFilters} role="group" aria-label="按目的地主题筛选">{["全部目的地", ...destinationThemes].map((name) => <button key={name} type="button" aria-pressed={theme === name} className={theme === name ? styles.filterActive : ""} onClick={() => setTheme(name)}>{name}</button>)}</div>
    <p className={styles.catalogNote} aria-live="polite">{visibleDestinations.length} 个目的地，{visibleDestinations.length} 种走进当地的方式。</p>
    <div className={styles.destinationsGrid}>{visibleDestinations.map((destination) => <DestinationCard key={destination.slug} destination={destination} />)}</div>
  </section>;
}
