import Link from "next/link";
import Icon from "./Icon";
import styles from "./SiteShell.module.css";
export default function SiteFooter() {
  return <footer className={styles.footer}><div className={`container ${styles.footerInner}`}><div className={styles.footerBrand}><Icon name="compass" size={24} /><strong>Travel Copilot</strong><span>Make room for discovery.</span></div><div className={styles.footerLinks}><Link href="/#journeys">Explore</Link><Link href="/plan">Plan a Journey</Link></div><p className={styles.footerNote}>Journey previews · Images are illustrations. Arrangements and quotes to be confirmed.</p></div></footer>;
}
