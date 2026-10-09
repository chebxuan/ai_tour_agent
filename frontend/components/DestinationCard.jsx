import Link from "next/link";
import copy from "@/data/destination_copy.json";
import { cityName } from "@/data/products";
import Icon from "./Icon";
import ScenicArt from "./ScenicArt";
import styles from "./Home.module.css";

export default function DestinationCard({ destination }) {
  const href = `/plan?destination=${destination.slug}`;
  return <article className={styles.destinationCard}>
    <Link href={href} className={styles.cardImage} tabIndex={-1} aria-hidden="true">
      <ScenicArt theme={destination.artTheme} />
      <span className={`placeholder-label ${styles.artLabel}`}>Illustration</span>
    </Link>
    <div className={styles.cardBody}>
      <div className={styles.cardTitle}><h3><Link href={href}>{cityName(destination.name)}</Link></h3></div>
      <p className={styles.cardStory}>{copy[destination.slug].story}</p>
      <div className={styles.cardTags}>{copy[destination.slug].tags.map((tag) => <span key={tag} className="tag">{tag}</span>)}</div>
      <Link href={href} className={styles.cardLink} aria-label={`Explore ${cityName(destination.name)}`}>Begin Your Journey <Icon size={18} /></Link>
    </div>
  </article>;
}
