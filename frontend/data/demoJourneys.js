// UI fixtures only: these ids and descriptions do not refer to published products.
export const demoJourneys = [
  { id: "demo-beijing", city: "北京", title: "北京 · 城市与文化", days: 3, theme: "city", tags: ["文化探索", "城市漫游"] },
  { id: "demo-shanghai", city: "上海", title: "上海 · 江岸与街巷", days: 2, theme: "river", tags: ["城市漫游", "轻松慢游"] },
  { id: "demo-guilin", city: "桂林", title: "桂林 · 山水之间", days: 3, theme: "mountains", tags: ["自然风光", "轻松慢游"] },
  { id: "demo-chengdu", city: "成都", title: "成都 · 生活的节奏", days: 3, theme: "mountains", tags: ["当地美食", "轻松慢游"] },
  { id: "demo-xian", city: "西安", title: "西安 · 古城时光", days: 2, theme: "city", tags: ["文化探索", "城市漫游"] },
  { id: "demo-hangzhou", city: "杭州", title: "杭州 · 湖畔漫步", days: 2, theme: "river", tags: ["自然风光", "轻松慢游"] },
];
export const demoCities = demoJourneys.map((journey) => journey.city);
export const interestOptions = ["文化探索", "当地美食", "自然风光", "亲子体验", "城市漫游", "轻松慢游"];
