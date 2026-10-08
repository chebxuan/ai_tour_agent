import { demoJourneys } from "@/data/demoJourneys";

// This builds layout examples only. Product matching and route generation remain in the backend.
export async function createDemoPreview(form, preferredId) {
  await new Promise((resolve) => setTimeout(resolve, 450));
  const candidates = demoJourneys.filter((journey) => journey.city === form.city && journey.days === Number(form.days));
  const journey = candidates.find((item) => item.id === preferredId) || candidates[0];
  if (!journey) return null;
  return {
    journey,
    request: { ...form, interests: [...form.interests] },
    days: Array.from({ length: journey.days }, (_, index) => ({
      number: index + 1,
      title: index === 0 ? "抵达与初识" : index === journey.days - 1 ? "慢游与告别" : "探索与体验",
      description: "这一天的景点、体验和交通说明将在正式产品内容整理后补充。",
      activities: [
        { time: "上午", title: "城市探索", description: "景点与活动内容待补充" },
        { time: "下午", title: "在地体验", description: "具体体验内容待补充" },
        { time: "傍晚", title: "留给自己的时间", description: "餐饮和自由活动建议待补充" },
      ],
    })),
  };
}
