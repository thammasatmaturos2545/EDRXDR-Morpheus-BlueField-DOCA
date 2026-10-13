import BluefieldHistory from "../bluefield-history";
import BluefieldShadow from "../shadow/bluefield-shadow";
export default function BluefieldPage() {
  return <main className="dashboard"><header className="topbar"><div><div className="eyebrow">NETWORK / ARCHIVED EVIDENCE</div><h1>BlueField Evidence</h1><p>สองมุมมองของข้อมูลทดลองย้อนหลัง · ไม่ควรนำจำนวนจากสองชุดมาบวกเป็นจำนวนเหตุการณ์ใหม่</p></div></header><BluefieldShadow/><details className="historical-details"><summary>ดูชุด Historical ต้นฉบับและรายละเอียด counters</summary><BluefieldHistory/></details></main>;
}
