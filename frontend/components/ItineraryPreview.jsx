import Link from "next/link";
import Icon from "./Icon";
import ScenicArt from "./ScenicArt";
import styles from "./Planner.module.css";

export default function ItineraryPreview({ result, status, dirty, error }) {
  return <section className={styles.previewCard} aria-labelledby="preview-heading" aria-busy={status === "loading"}>
    <div className={styles.previewHeading}><div><span className={styles.stepNumber}>02</span><h2 id="preview-heading">你的行程预览</h2></div><span className="tag">示意内容</span></div>
    <div className={styles.statusMessage} role="status">{status === "loading" ? "正在准备行程示意…" : dirty ? "需求已修改，点击预览按钮更新方案。" : status === "success" ? "行程示意已更新。" : ""}</div>
    {status === "loading" ? <div className={styles.emptyPreview}><div className={styles.loadingCompass}><Icon name="compass" size={54} /></div><h3>一段旅程，正在展开。</h3><p>正在准备界面示意内容。</p></div> : status === "error" ? <div className={styles.emptyPreview}><Icon name="compass" size={48} /><h3>预览暂时没有完成</h3><p>{error}</p><p>输入内容已保留，可以再次点击预览。</p></div> : status === "empty" ? <div className={styles.emptyPreview}><Icon name="compass" size={48} /><h3>换一种选择，看看更多可能。</h3><p>当前没有这个城市与天数组合的展示样例。<br />可选择 2 或 3 天，或从首页选择一条样例。</p><Link className="button button--secondary" href="/#journeys">浏览展示样例 <Icon size={18} /></Link></div> : !result ? <div className={styles.emptyPreview}><div className={styles.emptyArt}><ScenicArt theme="river" /><span className="placeholder-label">示意插画</span></div><p className="eyebrow">YOUR NEXT STORY STARTS HERE</p><h3>下一段故事，等你来开启。</h3><p>选择目的地和旅行偏好，<br />看看每一天可以怎样展开。</p><div className={styles.emptySteps}><span>选择需求</span><Icon size={15} /><span>预览行程</span><Icon size={15} /><span>继续调整</span></div></div> : <div className={styles.previewContent}>
      {dirty && <div className={styles.staleNotice}><Icon name="calendar" size={18} /><p>需求已修改。下方保留的是上一次预览，请更新后再查看。</p></div>}
      <div className={styles.resultHero}><ScenicArt theme={result.journey.theme} /><div><span className="placeholder-label">示意插画</span><p>{result.journey.city.toUpperCase()} · {result.journey.days} DAYS</p><h3>{result.journey.title}</h3></div></div>
      <div className={styles.resultSummary}><span><Icon name="calendar" size={17} />{result.journey.days} 天</span><span><Icon name="people" size={17} />{Number(result.request.adults) + Number(result.request.children) + Number(result.request.seniors)} 位旅客</span>{result.request.date && <span>{result.request.date}</span>}</div>
      <div className={styles.preferenceSummary}><span>你的偏好</span><p>{result.request.interests.join(" · ") || "暂未选择偏好"}</p></div>
      <div className={styles.timelineHeading}><h3>每一天，都值得期待。</h3><span>每日行程示意</span></div>
      <div className={styles.timeline}>{result.days.map((day) => <details className={styles.day} key={day.number} open><summary><span className={styles.dayNumber}>0{day.number}</span><div><span>DAY {day.number}</span><h4>{day.title}</h4></div><Icon name="chevron" size={18} /></summary><div className={styles.dayContent}><p>{day.description}</p><div className={styles.activities}>{day.activities.map((activity) => <div key={activity.time}><span>{activity.time}</span><div><strong>{activity.title}</strong><p>{activity.description}</p></div></div>)}</div></div></details>)}</div>
      <div className={styles.serviceSummary}><h3>服务与费用</h3><p>{[result.request.guide ? "导游陪同" : "自由探索", result.request.car ? "私人车辆" : "交通方式待确认"].join(" · ")}</p><span>报价待确认</span><small>服务安排与价格需结合正式产品确认，本页不提供销售报价。</small></div>
      {result.request.notes && <div className={styles.notesSummary}><h3>你补充的想法</h3><p>{result.request.notes}</p></div>}
      <p className={styles.resultNote}>以上为组件和排版示意，尚未进行真实产品匹配或路线生成。</p>
    </div>}
  </section>;
}
