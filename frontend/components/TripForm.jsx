import { demoCities, interestOptions } from "@/data/demoJourneys";
import Button from "./Button";
import Icon from "./Icon";
import styles from "./Planner.module.css";

export default function TripForm({ form, onChange, onSubmit, busy, preferredJourney, selectedDestination }) {
  function changeField(event) {
    const { name, value, type, checked } = event.target;
    onChange({ ...form, [name]: type === "checkbox" ? checked : value });
  }
  function toggleInterest(interest) {
    onChange({ ...form, interests: form.interests.includes(interest) ? form.interests.filter((item) => item !== interest) : [...form.interests, interest] });
  }
  return <form className={styles.formCard} onSubmit={onSubmit}>
    <div className={styles.cardHeading}><span className={styles.stepNumber}>01</span><div><h2>告诉我们，你想怎样旅行</h2><p>从几个简单的选择开始。</p></div></div>
    {selectedDestination && <div className={styles.selectedJourney}><Icon name="location" size={18} /><span>你想探索：{selectedDestination.name}<small>再选日期、天数和你喜欢的旅行方式</small></span></div>}
    {preferredJourney && <div className={styles.selectedJourney}><Icon name="check" size={18} /><span>已选择：{preferredJourney.title}<small>可在下方调整目的地与天数</small></span></div>}
    <fieldset className={styles.formFields} disabled={busy}>
      <section className={styles.formSection} aria-labelledby="destination-heading"><h3 id="destination-heading"><Icon name="location" size={19} />你的旅程</h3>
        {!selectedDestination && <label className={styles.field} htmlFor="trip-city"><span>想去哪里 <small>必填</small></span><select id="trip-city" name="city" value={form.city} onChange={changeField} required><option value="">选择一个目的地</option>{demoCities.map((city) => <option key={city} value={city}>{city}</option>)}</select></label>}
        <div className={styles.fieldRow}><label className={styles.field} htmlFor="trip-date"><span>出发日期 <small>可选</small></span><input id="trip-date" name="date" type="date" value={form.date} onChange={changeField} /></label><label className={styles.field} htmlFor="trip-days"><span>旅行天数</span><select id="trip-days" name="days" value={form.days} onChange={changeField}>{Array.from({ length: 10 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1} 天</option>)}</select></label></div>
      </section>
      <section className={styles.formSection} aria-labelledby="travelers-heading"><h3 id="travelers-heading"><Icon name="people" size={19} />与谁同行</h3><div className={styles.peopleFields}>{[{ name: "adults", label: "成人", min: 1 }, { name: "children", label: "儿童", min: 0 }, { name: "seniors", label: "长者", min: 0 }].map((person) => <label className={styles.field} key={person.name} htmlFor={`trip-${person.name}`}><span>{person.label}</span><input id={`trip-${person.name}`} name={person.name} type="number" min={person.min} max="20" required value={form[person.name]} onChange={changeField} /></label>)}</div></section>
      <fieldset className={styles.interestFieldset}><legend><Icon name="leaf" size={19} />喜欢怎样的旅程</legend><p>选出让你心动的体验，可多选。</p><div className={styles.interests}>{interestOptions.map((interest) => <button key={interest} type="button" aria-pressed={form.interests.includes(interest)} className={form.interests.includes(interest) ? styles.interestSelected : ""} onClick={() => toggleInterest(interest)}>{form.interests.includes(interest) && <Icon name="check" size={14} />}{interest}</button>)}</div></fieldset>
      <section className={styles.services}><h3>服务偏好</h3><label><input name="guide" type="checkbox" checked={form.guide} onChange={changeField} /><span>希望有导游陪同</span></label><label><input name="car" type="checkbox" checked={form.car} onChange={changeField} /><span>希望使用私人车辆</span></label></section>
      <details className={styles.extraNotes}><summary>还有其他想法？<Icon name="chevron" size={16} /></summary><label className={styles.field} htmlFor="trip-notes"><span>告诉我们你的期待</span><textarea id="trip-notes" name="notes" value={form.notes} onChange={changeField} rows={3} maxLength={2000} placeholder="例如：想慢一点，或希望安排更多亲子体验。" /></label><p>本轮仅展示输入，不进行 AI 解析。</p></details>
      <Button type="submit" className={styles.generateButton} disabled={busy}>{busy ? <><span className={styles.spinner} />正在准备示意预览</> : <>预览我的旅程 <Icon /></>}</Button>
      <p className={styles.formNote}>当前为交互演示，不会提交个人信息或产生订单。</p>
    </fieldset>
  </form>;
}
