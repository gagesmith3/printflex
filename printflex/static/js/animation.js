// Placeholder print animation. Each phase renders purely from its progress t (0..1), so the
// display can join a print midway (after a reload) and land on the right frame.
(function () {
  "use strict";

  const PHASE_LABELS = { receive: "RECEIVING", compose: "COMPOSING", print: "PRINTING", done: "COMPLETE" };
  const PHASE_ORDER = ["receive", "compose", "print", "done"];
  const PIXEL_STEPS = [6, 12, 24, 48, 96, 0]; // cells across; 0 = full resolution
  const FULL = PIXEL_STEPS.length - 1;
  const MASK_HEIGHT = 574; // .printer__bay height + .print-mask bottom overhang
  const BAR_WIDTH = 20;
  const MAX_LOG_LINES = 18;

  function scriptFor(card) {
    return {
      receive: [
        "> DIAL REMOTE TERMINAL ....... OK",
        "> HANDSHAKE 9600 BAUD ........ OK",
        "> RECEIVING IMAGE DATA",
        "> SUBJECT: " + card.last + ", " + card.first,
        "> CHECKSUM ................... OK",
      ],
      compose: [
        "> LOAD TEMPLATE " + card.state_abbr + "-DL/90",
        "> DITHER PORTRAIT ............ OK",
        "> ASSIGN DL# " + card.dl_number,
        "> SET EXPIRATION " + card.exp,
        "> LAYOUT ..................... OK",
      ],
      print: [
        "> WARM PRINT HEAD ............ OK",
        "> PASS 1/3  CYAN",
        "> PASS 2/3  MAGENTA",
        "> PASS 3/3  YELLOW",
        "> APPLY LAMINATE ............. OK",
      ],
      done: ["", "*** JOB COMPLETE - REMOVE CARD ***"],
    };
  }

  // Lines appear one after another; the newest one types out with a block cursor.
  function typeLines(lines, t) {
    if (t >= 1) return lines.slice();
    const exact = t * lines.length;
    const whole = Math.floor(exact);
    const shown = lines.slice(0, whole);
    const line = lines[whole];
    if (line !== undefined) shown.push(line.slice(0, Math.floor((exact - whole) * line.length)) + "█");
    return shown;
  }

  function progressBar(fraction) {
    const filled = Math.round(fraction * BAR_WIDTH);
    const percent = String(Math.floor(fraction * 100)).padStart(3, " ");
    return "[" + "█".repeat(filled) + "░".repeat(BAR_WIDTH - filled) + "] " + percent + "%";
  }

  function create(root) {
    const els = {
      card: root.querySelector("#card"),
      photo: root.querySelector("#card-photo"),
      ghost: root.querySelector("#card-ghost"),
      fields: Array.from(root.querySelectorAll("#card [data-field]")),
      log: root.querySelector("#log"),
      progress: root.querySelector("#progress"),
      phaseLabel: root.querySelector("#phase-label"),
      mask: root.querySelector("#print-mask"),
      head: root.querySelector("#print-head"),
      waiting: root.querySelector("#waiting"),
      banner: root.querySelector("#banner"),
    };
    const scratch = document.createElement("canvas");

    let job = null;
    let script = null;
    let image = null;
    let imageReady = false;
    let texts = [];
    let totalChars = 0;
    let phases = [];
    let total = 0;
    let startTime = 0;
    let frame = 0;
    let phaseShown = "";
    let photoStep = -1;
    let wantedStep = -1;
    let charsShown = -1;
    let logShown = null;
    let progressShown = null;

    function load(nextJob) {
      if (job && job.id === nextJob.id) return;
      job = nextJob;
      script = scriptFor(job.card);
      texts = els.fields.map((el) => String(job.card[el.dataset.field] || ""));
      totalChars = texts.reduce((sum, text) => sum + text.length, 0);
      charsShown = -1;
      photoStep = -1;
      imageReady = false;
      clear(els.photo);
      clear(els.ghost);
      image = new Image();
      image.onload = () => {
        imageReady = true;
        els.ghost.getContext("2d").drawImage(image, 0, 0, els.ghost.width, els.ghost.height);
        photoStep = -1;
        setPhotoStep(wantedStep);
      };
      image.src = job.photo_url;
    }

    function clear(canvas) {
      canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
    }

    // Draw the portrait at a pixelation level (-1 = blank).
    function setPhotoStep(step) {
      wantedStep = step;
      if (step === photoStep || !imageReady) return;
      photoStep = step;
      const canvas = els.photo;
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (step < 0) return;
      const cells = PIXEL_STEPS[step];
      if (cells === 0) {
        ctx.imageSmoothingEnabled = true;
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
        return;
      }
      scratch.width = cells;
      scratch.height = Math.round((cells * 4) / 3);
      scratch.getContext("2d").drawImage(image, 0, 0, scratch.width, scratch.height);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(scratch, 0, 0, canvas.width, canvas.height);
    }

    function setFieldChars(count) {
      if (count === charsShown) return;
      charsShown = count;
      let remaining = count;
      els.fields.forEach((el, i) => {
        const shown = texts[i].slice(0, Math.max(remaining, 0));
        remaining -= texts[i].length;
        if (el.textContent !== shown) el.textContent = shown;
      });
    }

    function enterPhase(name) {
      phaseShown = name;
      els.phaseLabel.textContent = PHASE_LABELS[name];
      els.card.classList.toggle("is-hidden", name === "receive");
      els.card.classList.toggle("is-wire", name === "compose");
      els.card.classList.toggle("is-done", name === "done");
      els.waiting.hidden = name !== "receive";
      els.mask.hidden = name !== "print";
      els.head.hidden = name !== "print";
      els.banner.hidden = name !== "done";
    }

    function render(name, t, overall) {
      if (name !== phaseShown) enterPhase(name);

      const lines = [];
      for (const phase of PHASE_ORDER) {
        if (phase === name) {
          lines.push(...typeLines(script[phase], t));
          break;
        }
        lines.push(...script[phase]);
      }
      const log = lines.slice(-MAX_LOG_LINES).join("\n");
      if (log !== logShown) els.log.textContent = logShown = log;
      const progress = progressBar(overall);
      if (progress !== progressShown) els.progress.textContent = progressShown = progress;

      if (name === "receive") {
        setPhotoStep(-1);
        setFieldChars(0);
      } else if (name === "compose") {
        setPhotoStep(Math.min(FULL, Math.floor(t * PIXEL_STEPS.length * 1.2)));
        setFieldChars(Math.floor(Math.min(1, t * 1.15) * totalChars));
      } else {
        setPhotoStep(FULL);
        setFieldChars(totalChars);
      }
      if (name === "print") {
        els.mask.style.transform = "scaleY(" + (1 - t) + ")";
        els.head.style.transform = "translateY(" + t * MASK_HEIGHT + "px)";
      }
    }

    function tick(now) {
      const elapsed = (now - startTime) / 1000;
      if (elapsed >= total) {
        render("print", 1, 1); // hold the last frame until the server says DONE
        frame = 0;
        return;
      }
      let offset = 0;
      for (const phase of phases) {
        if (elapsed < offset + phase.duration) {
          render(phase.name, (elapsed - offset) / phase.duration, elapsed / total);
          break;
        }
        offset += phase.duration;
      }
      frame = requestAnimationFrame(tick);
    }

    function stop() {
      cancelAnimationFrame(frame);
      frame = 0;
    }

    return {
      // Start (or join) a print that has been running for elapsedSeconds.
      play(nextJob, nextPhases, elapsedSeconds) {
        stop();
        load(nextJob);
        phases = nextPhases.map((phase) => ({ name: phase.name, duration: Math.max(0, phase.duration) }));
        total = phases.reduce((sum, phase) => sum + phase.duration, 0);
        startTime = performance.now() - Math.max(0, elapsedSeconds || 0) * 1000;
        phaseShown = "";
        frame = requestAnimationFrame(tick);
      },
      showDone(nextJob) {
        stop();
        load(nextJob);
        render("done", 1, 1);
      },
      stop() {
        stop();
        phaseShown = "";
      },
    };
  }

  window.PrintAnimation = { create };
})();
