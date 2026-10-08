import Link from "next/link";
import Icon from "./Icon";
import ScenicArt from "./ScenicArt";
import styles from "./Home.module.css";

export default function ProductCard({ journey }) {
  return <article className={styles.productCard}>
    <Link href={`/plan?journey=${journey.id}`} className={styles.cardImage} tabIndex={-1} aria-hidden="true"><ScenicArt theme={journey.theme} /><span className={styles.cityLabel}><Icon name="location" size={15} />{journey.city}</span><span className={`placeholder-label ${styles.artLabel}`}>示意插画</span></Link>
    <div className={styles.cardBody}>
      <div className={styles.cardMeta}><span>{journey.days} 天旅程</span><span>展示样例</span></div>
      <h3><Link href={`/plan?journey=${journey.id}`}>{journey.title}</Link></h3>
      <p>产品介绍与体验亮点，待下一轮完善。</p>
      <div className={styles.cardTags}>{journey.tags.map((tag) => <span key={tag} className="tag">{tag}</span>)}</div>
      <Link href={`/plan?journey=${journey.id}`} className={styles.cardLink} aria-label={`预览${journey.city}的示意行程`}>预览这条行程 <Icon size={18} /></Link>
    </div>
  </article>;
}
