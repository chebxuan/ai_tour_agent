import Link from "next/link";
import Icon from "./Icon";
import ScenicArt from "./ScenicArt";
import styles from "./Home.module.css";

export default function DestinationCard({ destination }) {
  const href = `/plan?destination=${destination.slug}`;
  return <article className={styles.destinationCard}>
    <Link href={href} className={styles.cardImage} tabIndex={-1} aria-hidden="true">
      <ScenicArt theme={destination.artTheme} />
      <span className={`placeholder-label ${styles.artLabel}`}>示意插画</span>
    </Link>
    <div className={styles.cardBody}>
      <div className={styles.cardTitle}><h3><Link href={href}>{destination.name}</Link></h3><span>{destination.englishName}</span></div>
      <p className={styles.cardStory}>{destination.story}</p>
      <div className={styles.cardTags}>{destination.culturalTags.map((tag) => <span key={tag} className="tag">{tag}</span>)}</div>
      <Link href={href} className={styles.cardLink} aria-label={`探索${destination.name}，设计旅程`}>从这里开启旅程 <Icon size={18} /></Link>
    </div>
  </article>;
}
