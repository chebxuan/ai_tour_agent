import Button from "./Button";
import Icon from "./Icon";
import ScenicArt from "./ScenicArt";
import DestinationCatalog from "./DestinationCatalog";
import styles from "./Home.module.css";

export default function HomePage() {
  return <main id="main" className="container">
    <section className={styles.hero} aria-labelledby="hero-title">
      <div className={styles.heroCopy}><p className="eyebrow"><span className={styles.shortLine} /> A JOURNEY, YOUR WAY</p><h1 id="hero-title">See China.<br />Feel <span>its local life.</span></h1><p className={styles.heroDescription}>From ancient lanes to mountain landscapes,<br />discover China at your own pace.</p><div className={styles.heroActions}><Button href="#journeys">Explore Destinations <Icon /></Button><Button href="/plan" variant="secondary">Plan My Journey</Button></div><div className={styles.heroNote}><Icon name="leaf" size={18} /><span>Choose a place · Add your experiences · Discover each day</span></div></div>
      <div className={styles.heroVisual}><ScenicArt /><div className={styles.visualTop}><span className="placeholder-label">Illustration</span><span>CHINA, AT YOUR PACE</span></div><div className={styles.visualBottom}><span>Take time to feel a place.</span><p>Leave room for the unexpected.</p></div><div className={styles.heroStamp}><Icon name="compass" size={26} /><span>DISCOVER<br />LOCAL LIFE</span></div></div>
    </section>
    <div className={styles.valueStrip}><div><Icon name="compass" /><span>Begin with curiosity</span></div><div><Icon name="calendar" /><span>Discover what each day holds</span></div><div><Icon name="leaf" /><span>Leave room for discovery</span></div></div>
    <DestinationCatalog />
    <section className={styles.howItWorks} aria-labelledby="how-title"><div><p className="eyebrow">A LITTLE PLANNING. MORE DISCOVERY.</p><h2 className="section-title" id="how-title">A journey shaped around you.</h2><p className="section-copy">Inspiration, with a clear next step.</p></div><div className={styles.steps}>{[{ title: "Find your destination", copy: "Explore places and choose a destination that speaks to you." }, { title: "Make it your own", copy: "Choose your dates, travellers and optional experiences." }, { title: "Discover your journey", copy: "Explore the stories and highlights of each day." }].map((step, index) => <div className={styles.step} key={step.title}><span>0{index + 1}</span><h3>{step.title}</h3><p>{step.copy}</p></div>)}</div></section>
    <section className={styles.customBanner}><div><p className="eyebrow">MAKE ROOM FOR YOUR OWN STORY</p><h2>Every journey starts with an idea.</h2><p>Choose a destination and see where curiosity takes you.</p></div><Button href="/plan" variant="light">Plan My Journey <Icon /></Button><Icon className={styles.bannerIcon} name="compass" size={190} /></section>
  </main>;
}
