// Print animation. Each phase renders purely from its progress t (0..1), so the display can
// join a print midway (after a reload) and land on the right frame.
(function () {
  "use strict";

  const PIXEL_STEPS = [6, 12, 24, 48, 96, 0]; // cells across; 0 = full resolution
  const FULL = PIXEL_STEPS.length - 1;
  const CARD_HEIGHT = 540; // .bay height
  const BAR_WIDTH = 20;
  const MAX_LOG_LINES = 14;

  const row = (label, value) => ("> " + label).padEnd(11, " ") + value;

  function scriptFor(job, phases) {
    const card = job.card;
    const seconds = phases.reduce((sum, phase) => sum + phase.duration, 0);
    return {
      receive: [row("img in", "600x800 jpg"), row("crop", "3:4 ok"), row("subject", card.last + ", " + card.first)],
      compose: [
        row("dob", card.dob + "  age " + card.age + "  ok"),
        row("addr", card.address1),
        row("dl#", card.dl_number),
        row("layout", "ok"),
      ],
      done: [row("done", seconds.toFixed(1) + "s"), row("tmp", "wiped")],
    };
  }

  // Lines appear one after another, the newest typing out character by character.
  function typeLines(lines, t) {
    if (t >= 1) return lines.slice();
    const exact = t * lines.length;
    const whole = Math.floor(exact);
    const shown = lines.slice(0, whole);
    const line = lines[whole];
    if (line !== undefined) shown.push(line.slice(0, Math.floor((exact - whole) * line.length)));
    return shown;
  }

  function progressRow(t) {
    const filled = Math.round(t * BAR_WIDTH);
    const percent = String(Math.floor(t * 100)).padStart(3, " ");
    return row("print", "[" + "█".repeat(filled) + "░".repeat(BAR_WIDTH - filled) + "] " + percent + "%");
  }

  function create(root) {
    const els = {
      card: root.querySelector("#card"),
      photo: root.querySelector("#card-photo"),
      ghost: root.querySelector("#card-ghost"),
      fields: Array.from(root.querySelectorAll("#card [data-field]")),
      log: root.querySelector("#log"),
      mask: root.querySelector("#print-mask"),
      head: root.querySelector("#print-head"),
      waiting: root.querySelector("#waiting"),
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

    function load(nextJob) {
      if (job && job.id === nextJob.id) return;
      job = nextJob;
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

    function setLog(lines) {
      const text = lines.slice(-MAX_LOG_LINES).join("\n");
      if (text !== logShown) els.log.textContent = logShown = text;
    }

    function enterPhase(name) {
      phaseShown = name;
      const empty = name === "idle" || name === "receive";
      els.card.classList.toggle("is-hidden", empty);
      els.card.classList.toggle("is-wire", name === "compose");
      els.card.classList.toggle("is-done", name === "done");
      els.waiting.hidden = !empty;
      els.mask.hidden = name !== "print";
      els.head.hidden = name !== "print";
    }

    function render(name, t) {
      if (name !== phaseShown) enterPhase(name);

      if (name === "receive") {
        setLog(typeLines(script.receive, t));
        setPhotoStep(-1);
        setFieldChars(0);
        return;
      }
      if (name === "compose") {
        setLog(script.receive.concat(typeLines(script.compose, t)));
        setPhotoStep(Math.min(FULL, Math.floor(t * PIXEL_STEPS.length * 1.2)));
        setFieldChars(Math.floor(Math.min(1, t * 1.15) * totalChars));
        return;
      }

      // print and done; the trailing "" puts the cursor on its own line
      const lines = script.receive.concat(script.compose, [progressRow(name === "print" ? t : 1)]);
      setLog(name === "done" ? lines.concat(script.done, [""]) : lines.concat([""]));
      setPhotoStep(FULL);
      setFieldChars(totalChars);
      if (name === "print") {
        els.mask.style.transform = "scaleY(" + (1 - t) + ")";
        els.head.style.transform = "translateY(" + t * CARD_HEIGHT + "px)";
      }
    }

    function tick(now) {
      const elapsed = (now - startTime) / 1000;
      if (elapsed >= total) {
        render("print", 1); // hold the last frame until the server says DONE
        frame = 0;
        return;
      }
      let offset = 0;
      for (const phase of phases) {
        if (elapsed < offset + phase.duration) {
          render(phase.name, (elapsed - offset) / phase.duration);
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
      // Empty preview with the given log lines (idle and loaded screens).
      idle(lines) {
        stop();
        enterPhase("idle");
        setLog(lines);
      },
      // Start (or join) a print that has been running for elapsedSeconds.
      play(nextJob, nextPhases, elapsedSeconds) {
        stop();
        load(nextJob);
        phases = nextPhases.map((phase) => ({ name: phase.name, duration: Math.max(0, phase.duration) }));
        total = phases.reduce((sum, phase) => sum + phase.duration, 0);
        script = scriptFor(job, phases);
        startTime = performance.now() - Math.max(0, elapsedSeconds || 0) * 1000;
        phaseShown = "";
        frame = requestAnimationFrame(tick);
      },
      showDone(nextJob, nextPhases) {
        stop();
        load(nextJob);
        script = scriptFor(job, nextPhases || []);
        phaseShown = "";
        render("done", 1);
      },
    };
  }

  window.PrintAnimation = { create };
})();
