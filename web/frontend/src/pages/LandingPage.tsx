import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import confetti from "canvas-confetti";
import { KairosLogo } from "../components/KairosLogo";
import { ThemeSwitcher } from "../theme";

const RIBBON_COLORS = [
  "#d4a24e",
  "#e9c46a",
  "#f4e3b2",
  "#c44536",
  "#7a8b6f",
  "#ffffff",
];

// Fire streamer ribbons inward from both screen edges.
function fireSideRibbons() {
  const duration = 1100;
  const end = Date.now() + duration;

  const shoot = () => {
    const base = {
      particleCount: 7,
      startVelocity: 55,
      spread: 50,
      ticks: 320,
      gravity: 0.9,
      scalar: 1.15,
      colors: RIBBON_COLORS,
      // long, thin "ribbon" particles rather than dots
      shapes: ["square"] as confetti.Shape[],
      drift: 0,
    };
    // left edge → up-right
    confetti({ ...base, angle: 60, origin: { x: 0, y: 0.65 } });
    // right edge → up-left
    confetti({ ...base, angle: 120, origin: { x: 1, y: 0.65 } });

    if (Date.now() < end) requestAnimationFrame(shoot);
  };
  shoot();
}

const PLACEHOLDERS = [
  "1990年5月15日，北京出生，男，事业方向怎么选？",
  "我适合创业还是稳定上班？",
  "下个月签约时机合适吗？",
  "我的性格优势和短板是什么？",
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [phIndex, setPhIndex] = useState(0);
  const storyRef = useRef<HTMLElement>(null);
  const finaleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (input.trim()) return;
    const id = window.setTimeout(
      () => setPhIndex((i) => (i + 1) % PLACEHOLDERS.length),
      3200,
    );
    return () => window.clearTimeout(id);
  }, [input, phIndex]);

  // Scroll reveal for story sections
  useEffect(() => {
    const root = storyRef.current;
    if (!root) return;
    const sections = root.querySelectorAll<HTMLElement>(".story__section");
    if (!sections.length) return;

    if (
      typeof IntersectionObserver === "undefined" ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      sections.forEach((s) => s.setAttribute("data-revealed", "true"));
      return;
    }

    root.setAttribute("data-motion-ready", "true");
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            (e.target as HTMLElement).setAttribute("data-revealed", "true");
            io.unobserve(e.target);
          }
        }
      },
      { threshold: 0.18, rootMargin: "0px 0px -8% 0px" },
    );
    sections.forEach((s) => io.observe(s));
    return () => io.disconnect();
  }, []);

  // Celebrate when the user scrolls all the way to the bottom (finale band).
  useEffect(() => {
    const finale = finaleRef.current;
    if (!finale) return;
    if (
      typeof IntersectionObserver === "undefined" ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return;
    }

    let armed = true; // fire once per arrival; re-arm after scrolling away
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting && armed) {
            armed = false;
            fireSideRibbons();
          } else if (!e.isIntersecting) {
            armed = true;
          }
        }
      },
      { threshold: 0.6 },
    );
    io.observe(finale);
    return () => io.disconnect();
  }, []);

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

  const scrollToStory = () => {
    const story = document.querySelector(".landing__story");
    if (story) {
      story.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="oracle landing">
      <div className="oracle__grain" aria-hidden />
      <div className="oracle__glow" aria-hidden />

      <header className="oracle-header oracle-header--landing">
        <div className="oracle-header__brand">
          <KairosLogo size={44} className="oracle-header__logo" />
          <span className="oracle-header__mark">Kairos</span>
        </div>
        <nav className="oracle-header__actions">
          <ThemeSwitcher />
          <button
            type="button"
            className="oracle-header__cta"
            onClick={() => navigate("/session")}
          >
            开始对话
          </button>
        </nav>
      </header>

      <main className="landing__main">
        {/* ── HERO ── */}
        <section className="landing__hero" aria-labelledby="landing-title">
          <KairosLogo size={68} className="landing__hero-logo" />
          <div className="oracle-empty__eyebrow">看清局势 · 把握时机</div>
          <h1 id="landing-title" className="oracle-empty__title">
            Kairos
          </h1>
          <p className="oracle-empty__text">
            告诉我你的出生信息和想了解的问题，我会从多个维度帮你分析当下的走向，给出有参考价值的建议。
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
                aria-label="输入你的问题"
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

          <button
            type="button"
            className="landing__scroll-hint"
            onClick={scrollToStory}
            aria-label="向下滚动查看使用说明"
          >
            <span>向下看看怎么用</span>
            <span className="landing__scroll-arrow">↓</span>
          </button>
        </section>

        {/* ── STORY (long-scroll product walkthrough) ── */}
        <section className="landing__story" ref={storyRef}>
          <article className="story__section" data-n="01">
            <div className="story__col story__col--text">
              <span className="story__num">01</span>
              <h2 className="story__title">一句话，开局</h2>
              <p className="story__desc">
                不用填冗长的表单。一句大白话，说清你的生辰和想问的事——剩下的交给推演。
              </p>
            </div>
            <div className="story__col story__col--demo">
              <div className="demo demo--chat">
                <div className="demo__bubble demo__bubble--user">
                  1990年5月15日，北京出生，男，事业方向怎么选？
                </div>
                <div className="demo__caption">自然语言 · 一句话即可</div>
              </div>
            </div>
          </article>

          <article className="story__section" data-n="02">
            <div className="story__col story__col--text">
              <span className="story__num">02</span>
              <h2 className="story__title">多维拆解，不止一面</h2>
              <p className="story__desc">
                格局、用神、大运、流年——从根基到当下气势，逐层展开你的命局，不只给你一个笼统结论。
              </p>
            </div>
            <div className="story__col story__col--demo">
              <div className="demo demo--dims">
                <div className="demo__dim">
                  <span className="demo__dim-label">格局</span>
                  <span className="demo__dim-value">庚金日主 · 建禄</span>
                </div>
                <div className="demo__dim">
                  <span className="demo__dim-label">用神</span>
                  <span className="demo__dim-value">取丁火 · 喜湿土</span>
                </div>
                <div className="demo__dim">
                  <span className="demo__dim-label">大运</span>
                  <span className="demo__dim-value">丁未运 · 32岁入</span>
                </div>
                <div className="demo__dim">
                  <span className="demo__dim-label">流年</span>
                  <span className="demo__dim-value">丙午 · 2026</span>
                </div>
              </div>
            </div>
          </article>

          <article className="story__section" data-n="03">
            <div className="story__col story__col--text">
              <span className="story__num">03</span>
              <h2 className="story__title">推演可见，不是黑箱</h2>
              <p className="story__desc">
                每一步推演都有依据。起承转合，你能看见结论是怎么一步步走出来的，而不是一句不可质疑的断语。
              </p>
            </div>
            <div className="story__col story__col--demo">
              <div className="demo demo--trace">
                <ol className="demo__trace-list">
                  <li>
                    <span className="demo__trace-tag">起</span>
                    <span>日主庚金，生于巳月，火旺金弱</span>
                  </li>
                  <li>
                    <span className="demo__trace-tag">承</span>
                    <span>巳中庚金长生，印星暗助</span>
                  </li>
                  <li>
                    <span className="demo__trace-tag">转</span>
                    <span>用神取丁火炼金，喜湿土养根</span>
                  </li>
                  <li>
                    <span className="demo__trace-tag">合</span>
                    <span>宜火土行业，东南方利，忌水冷</span>
                  </li>
                </ol>
              </div>
            </div>
          </article>

          <article className="story__section" data-n="04">
            <div className="story__col story__col--text">
              <span className="story__num">04</span>
              <h2 className="story__title">给的是建议，不是玄话</h2>
              <p className="story__desc">
                不说"必有大灾"这种废话。给的是"下个月午火当令，利于签约"这种带时机、可执行的判断。
              </p>
            </div>
            <div className="story__col story__col--demo">
              <div className="demo demo--advice">
                <div className="demo__advice-head">
                  <span className="demo__advice-when">下个月 · 午月</span>
                  <span className="demo__tag demo__tag--go">宜</span>
                </div>
                <p className="demo__advice-body">
                  火旺当令，正合用神。利于签约、求职、开新局。
                </p>
                <div className="demo__advice-foot">
                  <span className="demo__tag demo__tag--no">忌</span>
                  <span>子日 · 正北远行 · 水冷灭火</span>
                </div>
              </div>
            </div>
          </article>

          <article className="story__section story__section--cta" data-n="05">
            <div className="story__col story__col--text">
              <span className="story__num">05</span>
              <h2 className="story__title">每一局，都留有案卷</h2>
              <p className="story__desc">
                所有对话自动归档。隔半年回看，当时的判断是否应验、局势怎么走的，一目了然。
              </p>
            </div>
            <div className="story__col story__col--demo">
              <div className="demo demo--archive">
                <div className="demo__arc-row">
                  <span className="demo__arc-date">06·18</span>
                  <span className="demo__arc-topic">事业方向该不该转</span>
                  <span className="demo__arc-dot" />
                </div>
                <div className="demo__arc-row">
                  <span className="demo__arc-date">06·02</span>
                  <span className="demo__arc-topic">感情走向与时机</span>
                  <span className="demo__arc-dot" />
                </div>
                <div className="demo__arc-row">
                  <span className="demo__arc-date">05·21</span>
                  <span className="demo__arc-topic">今年适合创业吗</span>
                  <span className="demo__arc-dot" />
                </div>
              </div>
            </div>
          </article>

          {/* Final CTA band */}
          <div className="story__finale" ref={finaleRef}>
            <p className="story__finale-line">局势已明，时机已至。</p>
            <button
              type="button"
              className="story__finale-btn"
              onClick={() => navigate("/session")}
            >
              开始对话 →
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
