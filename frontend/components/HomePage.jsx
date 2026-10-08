import Button from "./Button";
import Icon from "./Icon";
import ScenicArt from "./ScenicArt";
import JourneyCatalog from "./JourneyCatalog";
import styles from "./Home.module.css";

export default function HomePage() {
  return <main id="main" className="container">
    <section className={styles.hero} aria-labelledby="hero-title">
      <div className={styles.heroCopy}><p className="eyebrow"><span className={styles.shortLine} /> A JOURNEY, YOUR WAY</p><h1 id="hero-title">走进风景，<br />也走进<span>当地的生活。</span></h1><p className={styles.heroDescription}>从古城街巷到山水之间，<br />发现中国，也找到属于你的旅行节奏。</p><div className={styles.heroActions}><Button href="#journeys">探索行程 <Icon /></Button><Button href="/plan" variant="secondary">定制我的旅程</Button></div><div className={styles.heroNote}><Icon name="leaf" size={18} /><span>选择目的地 · 按你的偏好 · 预览每一天</span></div></div>
      <div className={styles.heroVisual}><ScenicArt /><div className={styles.visualTop}><span className="placeholder-label">风景示意插画</span><span>CHINA, AT YOUR PACE</span></div><div className={styles.visualBottom}><span>不赶路，去感受。</span><p>留一点时间，给旅途中的意外惊喜。</p></div><div className={styles.heroStamp}><Icon name="compass" size={26} /><span>探索<br />另一种日常</span></div></div>
    </section>
    <div className={styles.valueStrip}><div><Icon name="compass" /><span>从你的兴趣出发</span></div><div><Icon name="calendar" /><span>让每一天清晰可见</span></div><div><Icon name="leaf" /><span>给旅程留一点余地</span></div></div>
    <JourneyCatalog />
    <section className={styles.howItWorks} aria-labelledby="how-title"><div><p className="eyebrow">A LITTLE PLANNING. MORE DISCOVERY.</p><h2 className="section-title" id="how-title">你的旅程，由你来定义。</h2><p className="section-copy">有灵感，也有清晰的下一步。</p></div><div className={styles.steps}>{[{ title: "找到心动的目的地", copy: "浏览旅行灵感，选择想探索的城市。" }, { title: "告诉我们你的偏好", copy: "填入日期、同行人数和喜欢的旅行方式。" }, { title: "看看旅程如何展开", copy: "预览每日安排，按你的节奏继续调整。" }].map((step, index) => <div className={styles.step} key={step.title}><span>0{index + 1}</span><h3>{step.title}</h3><p>{step.copy}</p></div>)}</div></section>
    <section className={styles.customBanner}><div><p className="eyebrow">MAKE ROOM FOR YOUR OWN STORY</p><h2>还没有想好？从一个想法开始。</h2><p>选择你想去的地方，看看一段旅程的模样。</p></div><Button href="/plan" variant="light">设计我的旅程 <Icon /></Button><Icon className={styles.bannerIcon} name="compass" size={190} /></section>
  </main>;
}
