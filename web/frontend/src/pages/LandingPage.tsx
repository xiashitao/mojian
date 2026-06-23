import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/logo.png";
import { ThemeSwitcher } from "../theme";

const PLACEHOLDERS = [
  "1990年5月15日早上8点半，北京出生，男，想看事业",
  "我适合创业还是稳定上班？",
  "我想看感情里的相处模式",
  "我的性格优势和短板是什么？",
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [phIndex, setPhIndex] = useState(0);

  useEffect(() => {
    if (input.trim()) return;
    const id = window.setTimeout(
      () => setPhIndex((i) => (i + 1) % PLACEHOLDERS.length),
      3200,
    );
    return () => window.clearTimeout(id);
  }, [input, phIndex]);

  const handleSubmit = (text: string) => {
    const t = text.trim() || PLACEHOLDERS[phIndex];
    if (!t) return;
    navigate("/session", { state: { initialMessage: t } });
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(input);
    }
  };

  return (
    <div className="oracle landing">
      <div className="oracle__grain" aria-hidden />
      <div className="oracle__glow" aria-hidden />

      <header className="oracle-header oracle-header--landing">
        <div className="oracle-header__brand">
          <img className="oracle-header__logo" src={logo} alt="墨鉴" />
          <span className="oracle-header__mark">墨鉴</span>
        </div>
        <nav className="oracle-header__actions">
          <ThemeSwitcher />
          <button
            type="button"
            className="oracle-header__cta"
            onClick={() => navigate("/session")}
          >
            开始问诊
          </button>
        </nav>
      </header>

      <main className="landing__main">
        <section className="landing__hero" aria-labelledby="landing-title">
          <img className="landing__hero-logo" src={logo} alt="墨鉴" />
          <div className="oracle-empty__eyebrow">问事入盘 · 观时识势</div>
          <h1 id="landing-title" className="oracle-empty__title">
            墨鉴
          </h1>
          <p className="oracle-empty__text">
            说出生辰、地点、性别和所问之事，我会从时间与结构出发，帮你看清当下的走向与选择边界。
          </p>

          <form
            className="landing__composer"
            onSubmit={(event) => {
              event.preventDefault();
              handleSubmit(input);
            }}
          >
            <div className="landing__input-wrap">
              {!input && (
                <span key={phIndex} className="landing__placeholder">
                  {PLACEHOLDERS[phIndex]}
                </span>
              )}
              <input
                className="composer__input landing__input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                aria-label="输入想咨询的问题"
                autoFocus
              />
            </div>
            <button
              type="submit"
              className="landing__send"
              aria-label="发送"
            >
              →
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
