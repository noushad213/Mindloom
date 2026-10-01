import { useEffect } from "react";
import "./LandingPage.css";

function MindloomMark() {
  return (
    <span className="landingMark" aria-hidden="true">
      <i />
      <i />
      <i />
    </span>
  );
}

function ResearchMap() {
  return (
    <div className="mapStage" aria-label="A sample research graph connecting articles, papers, and ideas">
      <div className="mapChrome">
        <div className="mapChromeDots"><i /><i /><i /></div>
        <span>FIELD NOTES / 04</span>
        <span className="mapLive"><i /> SAMPLE WORKSPACE</span>
      </div>
      <div className="mapCanvas">
        <svg className="mapLines" viewBox="0 0 720 440" role="img" aria-label="Related research sources linked by evidence">
          <path className="mapEdge edgeOne" d="M135 117 C205 115 205 197 278 205" />
          <path className="mapEdge edgeTwo" d="M280 205 C351 205 364 119 443 115" />
          <path className="mapEdge edgeThree" d="M280 205 C359 210 353 302 443 310" />
          <path className="mapEdge edgeFour" d="M443 115 C516 112 519 201 590 205" />
          <path className="mapEdge edgeFive" d="M443 310 C519 308 521 216 590 205" />
          <circle className="mapJunction" cx="280" cy="205" r="4" />
        </svg>
        <div className="mapLabel labelResearch">RESEARCH THREAD <span>06 SOURCES</span></div>
        <div className="mapNode nodePaper"><span className="nodeGlyph glyphPaper">P</span><span><b>Attention Is All You Need</b><small>arxiv.org · paper</small></span></div>
        <div className="mapNode nodeHub"><span className="nodeGlyph glyphHub">✳</span><span><b>Language models</b><small>Topic · 4 connections</small></span></div>
        <div className="mapNode nodeDocs"><span className="nodeGlyph glyphDocs">D</span><span><b>Transformer · guide</b><small>huggingface.co · docs</small></span></div>
        <div className="mapNode nodeArticle"><span className="nodeGlyph glyphArticle">A</span><span><b>Scaling laws for neural models</b><small>arxiv.org · paper</small></span></div>
        <div className="mapNode nodeNotes"><span className="nodeGlyph glyphNotes">N</span><span><b>Why attention scales</b><small>Your note · 2 highlights</small></span></div>
        <div className="evidenceTag"><span>↗</span> shared idea <b>attention</b></div>
        <div className="mapFoot"><span>01 — 05</span><span>LINKS WITH EVIDENCE</span><span>↗</span></div>
      </div>
      <div className="mapCaption"><span>AN EXAMPLE OF A LIVING RESEARCH MAP</span><span>NOT ANOTHER BOOKMARK FOLDER</span></div>
    </div>
  );
}

function LandingPage() {
  useEffect(() => {
    const elements = document.querySelectorAll<HTMLElement>(".reveal");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      elements.forEach((element) => element.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14, rootMargin: "0px 0px -40px 0px" },
    );
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  return (
    <main className="landingPage">
      <div className="scrollProgress" aria-hidden="true" />
      <header className="landingNav">
        <a className="landingBrand" href="#top" aria-label="Mindloom home"><MindloomMark />mindloom<span className="brandPeriod">.</span></a>
        <nav aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#principles">Principles</a>
        </nav>
        <a className="navWorkspace" href="/app">Open workspace <span aria-hidden="true">↗</span></a>
      </header>

      <section className="landingHero" id="top">
        <div className="heroCopy">
          <p className="heroEyebrow"><span /> A VISUAL RESEARCH WORKSPACE</p>
          <h1>Good research<br />has <em>a shape.</em></h1>
          <p className="heroLead">Mindloom turns the tabs you choose into a living map of sources, ideas, and the connections between them.</p>
          <div className="heroActions">
            <a className="buttonPrimary" href="/app">Explore the workspace <span aria-hidden="true">↗</span></a>
            <a className="textLink" href="#how-it-works">See how it takes shape <span aria-hidden="true">↓</span></a>
          </div>
          <p className="heroNote"><span className="privacyGlyph">◎</span> Your browser. Your choice. Capture starts when you do.</p>
        </div>
        <div className="heroVisual"><ResearchMap /></div>
        <div className="heroIndex"><span>01 / 03</span><span>FROM OPEN TABS TO OPEN QUESTIONS</span><span>SCROLL TO EXPLORE ↓</span></div>
      </section>

      <section className="thesisBand" id="how-it-works">
        <div className="thesisIntro reveal">
          <p className="sectionKicker">THE IDEA, IN THREE MOVES</p>
          <h2>From scattered<br />to <em>connected.</em></h2>
          <p className="thesisBody">A browser session is full of clues. Mindloom helps you keep the useful ones, find the relationships, and stay in charge of what they mean.</p>
          <a className="lightLink" href="/app">See the workspace <span aria-hidden="true">↗</span></a>
        </div>
        <div className="storyTrack">
          <div className="storyArt" aria-hidden="true">
            <div className="storyOrbit orbitOuter" />
            <div className="storyOrbit orbitInner" />
            <svg viewBox="0 0 520 520" className="storyConnections">
              <path pathLength="1" d="M112 137 255 235 397 126M255 235l-96 151 190 22 48-282M112 137l47 249M397 126l-38 282" />
              <path pathLength="1" d="M112 137 397 126M255 235l152 54M159 386l200 22" />
            </svg>
            <span className="storyDot dotA">01</span><span className="storyDot dotB">02</span><span className="storyDot dotC">03</span><span className="storyDot dotD">04</span><span className="storyDot dotE">05</span>
            <span className="artAnnotation">A MAP THAT GROWS WITH YOU</span>
          </div>
          <article className="storyStep reveal">
            <span className="stepNumber">01 <i /> COLLECT</span>
            <h3>Start with the pages<br />you already found.</h3>
            <p>Choose when to capture. Mindloom saves the page, not just the tab, so closing your browser never erases your research.</p>
            <div className="stepFoot"><span>EXPLICIT BY DESIGN</span><span>01 — 03</span></div>
          </article>
          <article className="storyStep reveal">
            <span className="stepNumber">02 <i /> CONNECT</span>
            <h3>See the ideas<br />between the links.</h3>
            <p>Related sources gather into a visual graph. Suggested connections come with evidence, so you can inspect the why.</p>
            <div className="stepFoot"><span>EVIDENCE, NOT MAGIC</span><span>02 — 03</span></div>
          </article>
          <article className="storyStep reveal">
            <span className="stepNumber">03 <i /> MAKE IT YOURS</span>
            <h3>Your thinking stays<br />in the driver's seat.</h3>
            <p>Add notes, tags, groups, and your own links. Manual decisions remain yours when the graph updates.</p>
            <div className="stepFoot"><span>HUMAN-EDITABLE</span><span>03 — 03</span></div>
          </article>
        </div>
      </section>

      <section className="capabilities" id="principles">
        <div className="capabilitiesHead reveal">
          <p className="sectionKicker">BUILT FOR THE WAY RESEARCH MOVES</p>
          <h2>Keep the thread.<br /><em>Lose the tab chaos.</em></h2>
          <p>A focused toolkit for following an idea from the first open page to the work you can share.</p>
        </div>
        <div className="capabilityList">
          <article className="capability reveal">
            <span className="capabilityIndex">01 / CAPTURE</span>
            <div className="capabilityIcon iconCapture"><i /><i /><i /></div>
            <div><h3>Choose what comes in.</h3><p>Collect eligible pages only after you start. Clear status and stop controls keep the process visible.</p></div>
            <span className="capabilityArrow" aria-hidden="true">↗</span>
          </article>
          <article className="capability reveal">
            <span className="capabilityIndex">02 / ORGANIZE</span>
            <div className="capabilityIcon iconOrganize"><i /><i /><i /></div>
            <div><h3>Find the shape of a topic.</h3><p>Explore suggested relationships, inspect their evidence, and shape the graph around your question.</p></div>
            <span className="capabilityArrow" aria-hidden="true">↗</span>
          </article>
          <article className="capability reveal">
            <span className="capabilityIndex">03 / DEVELOP</span>
            <div className="capabilityIcon iconDevelop"><i>n</i><i>+</i><i>↗</i></div>
            <div><h3>Keep your thinking attached.</h3><p>Notes, tags, and workspaces give useful context a home beyond the browser session.</p></div>
            <span className="capabilityArrow" aria-hidden="true">↗</span>
          </article>
          <article className="capability reveal">
            <span className="capabilityIndex">04 / TAKE IT WITH YOU</span>
            <div className="capabilityIcon iconShare"><i>↗</i><i>↗</i><i>↗</i></div>
            <div><h3>Make the map useful elsewhere.</h3><p>Search across sources and export your workspace as structured JSON or readable Markdown.</p></div>
            <span className="capabilityArrow" aria-hidden="true">↗</span>
          </article>
        </div>
      </section>

      <section className="closingBand">
        <div className="closingTexture" aria-hidden="true" />
        <p className="sectionKicker">YOUR NEXT QUESTION IS ALREADY IN THERE</p>
        <h2>Make room for<br /><em>the connections.</em></h2>
        <p className="closingLead">Bring your research together, then follow it somewhere new.</p>
        <a className="buttonLight" href="/app">Enter Mindloom <span aria-hidden="true">↗</span></a>
        <div className="closingFoot"><span>MINDLOOM / VISUAL RESEARCH WORKSPACE</span><span>BUILT TO KEEP THE THREAD</span><a href="#top">BACK TO TOP ↑</a></div>
      </section>
      <footer className="landingFooter"><a className="landingBrand" href="#top"><MindloomMark />mindloom<span className="brandPeriod">.</span></a><p>Research is a process. Keep its connections.</p><a href="/app">Open workspace ↗</a></footer>
    </main>
  );
}

export default LandingPage;