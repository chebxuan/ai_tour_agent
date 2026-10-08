"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import Icon from "./Icon";
import styles from "./SiteShell.module.css";

export default function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const isPlan = pathname === "/plan";
  return <header className={styles.header}><div className={`container ${styles.headerInner}`}>
    <Link href="/" className={styles.brand} onClick={() => setOpen(false)} aria-label="行旅，返回首页"><span className={styles.mark}><Icon name="compass" size={28} /></span><span><strong>行旅</strong><small>TRAVEL COPILOT</small></span></Link>
    <button className={styles.menuButton} type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="site-nav" aria-label={open ? "关闭导航" : "打开导航"}><Icon name={open ? "close" : "menu"} /></button>
    <nav id="site-nav" className={`${styles.nav} ${open ? styles.navOpen : ""}`} aria-label="主导航">
      <Link href="/" aria-current={!isPlan ? "page" : undefined} onClick={() => setOpen(false)}>探索行程</Link>
      <Link href="/#destinations" onClick={() => setOpen(false)}>目的地</Link>
      <Link href="/plan" aria-current={isPlan ? "page" : undefined} onClick={() => setOpen(false)}>定制旅程</Link>
    </nav>
    <Link href="/plan" className={styles.headerCta} onClick={() => setOpen(false)}>设计我的旅程 <Icon size={16} /></Link>
  </div></header>;
}
