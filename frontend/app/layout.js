import "./globals.css";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";

export const metadata = {
  title: { default: "行旅 · 探索你的中国旅程", template: "%s · 行旅" },
  description: "探索旅行灵感，选择目的地与偏好，预览属于你的旅程。当前为界面演示版本。",
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN" data-scroll-behavior="smooth">
      <body>
        <a className="skip-link" href="#main">跳转到主要内容</a>
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
