import Link from "next/link";
import Icon from "./Icon";
import styles from "./SiteShell.module.css";
export default function SiteFooter() {
  return <footer className={styles.footer}><div className={`container ${styles.footerInner}`}><div className={styles.footerBrand}><Icon name="compass" size={24} /><strong>行旅</strong><span>让旅程，留一点余地。</span></div><div className={styles.footerLinks}><Link href="/#journeys">探索行程</Link><Link href="/plan">定制旅程</Link></div><p className={styles.footerNote}>界面预览版本 · 产品与行程内容暂为示意</p></div></footer>;
}
