'use strict';

const state = {
  lhsName: '',        
  varNames: [],        
  powers: {},        

  derivHints: [],       
  derivHintIdx: 0,        

  calcHints: [],       
  calcHintIdx: 0,        

  wrongContext: '',       
};

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text) e.textContent = text;
  return e;
};

function showErr(id, msg) {
  const e = $(id);
  if (!e) return;
  e.textContent = msg;
  e.classList.remove('hidden');
}

function hideErr(id) {
  const e = $(id);
  if (e) e.classList.add('hidden');
}

function goToScreen(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const target = $(screenId);
  if (target) {
    target.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  const restartBtn = $('btn-restart');
  if (restartBtn) {
    restartBtn.style.display = screenId === 'screen-equation' ? 'none' : 'inline-flex';
  }
}

function setProgressStep(activeStep) {

  for (let i = 1; i <= 4; i++) {
    const step = $(`pstep-${i}`);
    const line = $(`pline-${i}`);

    step.classList.remove('active', 'completed');
    if (line) line.classList.remove('completed');

    if (i < activeStep) {
      step.classList.add('completed');
      step.querySelector('.step-circle').textContent = '';  
      if (line) line.classList.add('completed');
    } else if (i === activeStep) {
      step.classList.add('active');
      step.querySelector('.step-circle').textContent = i;
    } else {
      step.querySelector('.step-circle').textContent = i;
    }
  }
}

function setExample(eq) {
  const input = $('eq-input');
  if (input) {
    input.value = eq;
    input.focus();
  }
  hideErr('eq-error');
}

async function parseEquation() {
  const raw = ($('eq-input').value || '').trim();
  if (!raw) {
    showErr('eq-error', 'Please enter an equation first.');
    return;
  }
  hideErr('eq-error');

  const btn = $('btn-parse');
  btn.disabled = true;
  btn.innerHTML = '<span>Analysing…</span>';

  try {
    const res = await fetch('/api/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ equation: raw }),
    });
    const data = await res.json();

    if (!data.success) {
      showErr('eq-error', data.error);
      return;
    }

    state.lhsName = data.lhs_name;
    state.varNames = data.var_names;
    state.powers = data.powers;

    buildDerivQuiz();
    setProgressStep(2);
    goToScreen('screen-derivative');

  } catch (e) {
    showErr('eq-error', 'Network error — please try again.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Analyse Equation</span><span class="btn-arrow">→</span>';
  }
}

function buildDerivQuiz() {
  const { lhsName, varNames } = state;

  const tpl = $('formula-template');
  tpl.innerHTML = '';   

  const lhsSpan = el('span', 'f-lhs');
  lhsSpan.textContent = `d${lhsName} / ${lhsName}`;
  const eqSpan = el('span', 'f-equals');
  eqSpan.textContent = ' = ';
  tpl.appendChild(lhsSpan);
  tpl.appendChild(eqSpan);

  const placeholder = varNames.map(v => `d${v}/${v}`).join(' + ');
  const inp = document.createElement('input');
  inp.type = 'text';
  inp.id = 'deriv-formula-input';
  inp.className = 'formula-inline-input';
  inp.placeholder = placeholder;
  inp.autocomplete = 'off';
  inp.spellcheck = false;
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') checkDerivative(); });
  tpl.appendChild(inp);

  const container = $('deriv-inputs');
  container.innerHTML = '';
  const tip = el('p', 'formula-input-hint',
    `Tip: write each term as d⟨var⟩/⟨var⟩, separated by " + ". `
  );
  container.appendChild(tip);

  state.derivHints = [];
  state.derivHintIdx = 0;
  const log = $('deriv-hints-log');
  if (log) log.innerHTML = '';
  $('btn-next-deriv-hint').classList.remove('hidden');
  $('btn-back-to-deriv').classList.add('hidden');
}

async function checkDerivative() {
  hideErr('deriv-error');

  const inp = $('deriv-formula-input');
  const formula = (inp ? inp.value : '').trim();

  if (!formula) {
    showErr('deriv-error', 'Please type the derivative formula (e.g. db/b + dh/h + dl/l).');
    return;
  }

  try {
    const res = await fetch('/api/check-deriv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ formula }),
    });
    const data = await res.json();

    if (!data.success) {
      showErr('deriv-error', data.error);
      return;
    }

    if (data.correct) {

      buildErrorInputs();
      setProgressStep(3);
      goToScreen('screen-errors');
    } else {

      state.wrongContext = 'derivative';
      $('wrong-title').textContent = 'Incorrect Derivative';
      $('wrong-subtitle').textContent =
        data.message || 'Your derivative formula is not quite right. Try again or see the hints.';
      goToScreen('screen-wrong');
    }
  } catch (e) {
    showErr('deriv-error', 'Network error — please try again.');
  }
}

async function loadAndShowDerivHints() {

  if (state.derivHints.length === 0) {
    try {
      const res = await fetch('/api/deriv-hints');
      const data = await res.json();
      if (!data.success) { alert(data.error); return; }
      state.derivHints = data.steps;
      state.derivHintIdx = 0;
    } catch (e) {
      alert('Network error — please try again.');
      return;
    }
  }

  const log = $('deriv-hints-log');
  log.innerHTML = '';
  state.derivHintIdx = 0;

  $('btn-next-deriv-hint').classList.remove('hidden');
  $('btn-back-to-deriv').classList.add('hidden');

  goToScreen('screen-deriv-hints');

  nextDerivHint();
}

function nextDerivHint() {
  const { derivHints, derivHintIdx } = state;
  if (derivHintIdx >= derivHints.length) return;

  const log = $('deriv-hints-log');
  const step = el('div', 'hint-step', derivHints[derivHintIdx]);

  if (derivHintIdx === derivHints.length - 1) {
    step.classList.add('hint-summary');
  }
  log.appendChild(step);
  step.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  state.derivHintIdx++;

  if (state.derivHintIdx >= derivHints.length) {
    $('btn-next-deriv-hint').classList.add('hidden');
    $('btn-back-to-deriv').classList.remove('hidden');
  }
}

function buildErrorInputs() {
  const container = $('error-inputs');
  container.innerHTML = '';

  state.varNames.forEach(v => {
    const p = state.powers[v];
    const row = el('div', 'var-row var-row-error');

    const lbl = el('div', 'var-label');
    const coefStr = Math.abs(p) === 1 ? '' : `  ·  power = ${Math.abs(p)}`;
    lbl.textContent = `% error for  ${v}${coefStr}`;
    row.appendChild(lbl);

    const inp = document.createElement('input');
    inp.type = 'number';
    inp.step = 'any';
    inp.min = '0';
    inp.className = 'var-input';
    inp.placeholder = 'e.g.  2';
    inp.id = `err-inp-${v}`;
    inp.dataset.var = v;
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') submitErrors();
    });
    row.appendChild(inp);

    container.appendChild(row);
  });
}

async function submitErrors() {
  hideErr('errors-error');

  const varErrors = {};
  for (const v of state.varNames) {
    const inp = $(`err-inp-${v}`);
    const val = (inp ? inp.value : '').trim();
    if (val === '') {
      showErr('errors-error', `Please enter a percentage error for '${v}'.`);
      return;
    }
    varErrors[v] = val;
  }

  try {
    const res = await fetch('/api/set-errors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ var_errors: varErrors }),
    });
    const data = await res.json();

    if (!data.success) {
      showErr('errors-error', data.error);
      return;
    }

    const summary = state.varNames
      .map(v => `%E(${v}) = ${varErrors[v]}%`)
      .join('  ·  ');
    $('answer-subtitle').textContent =
      `Given: ${summary}. Now calculate the total percentage error.`;

    state.calcHints = [];
    state.calcHintIdx = 0;
    const log = $('calc-hints-log');
    if (log) log.innerHTML = '';
    $('btn-next-calc-hint').classList.remove('hidden');
    $('btn-back-to-answer').classList.add('hidden');

    setProgressStep(4);
    goToScreen('screen-answer');

  } catch (e) {
    showErr('errors-error', 'Network error — please try again.');
  }
}

async function checkAnswer() {
  hideErr('answer-error');

  const raw = ($('answer-input').value || '').trim();
  if (raw === '') {
    showErr('answer-error', 'Please enter a number.');
    return;
  }

  try {
    const res = await fetch('/api/check-answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer: raw }),
    });
    const data = await res.json();

    if (!data.success) {
      showErr('answer-error', data.error);
      return;
    }

    if (data.correct) {

      $('success-answer-display').textContent =
        `%E(${state.lhsName})  =  ${raw}%  ✓`;
      setProgressStep(5);   
      goToScreen('screen-success');
    } else {

      state.wrongContext = 'answer';
      $('wrong-title').textContent = 'Incorrect Answer';
      $('wrong-subtitle').textContent =
        'That answer is not quite right. Would you like to try again or see the steps?';
      goToScreen('screen-wrong');
    }
  } catch (e) {
    showErr('answer-error', 'Network error — please try again.');
  }
}

async function loadAndShowCalcHints() {
  if (state.calcHints.length === 0) {
    try {
      const res = await fetch('/api/calc-hints');
      const data = await res.json();
      if (!data.success) { alert(data.error); return; }
      state.calcHints = data.steps;
      state.calcHintIdx = 0;
    } catch (e) {
      alert('Network error — please try again.');
      return;
    }
  }

  const log = $('calc-hints-log');
  log.innerHTML = '';
  state.calcHintIdx = 0;

  $('btn-next-calc-hint').classList.remove('hidden');
  $('btn-back-to-answer').classList.add('hidden');

  goToScreen('screen-calc-hints');
  nextCalcHint();
}

function nextCalcHint() {
  const { calcHints, calcHintIdx } = state;
  if (calcHintIdx >= calcHints.length) return;

  const log = $('calc-hints-log');
  const step = el('div', 'hint-step', calcHints[calcHintIdx]);

  if (calcHintIdx === calcHints.length - 1) {
    step.classList.add('hint-summary');
  }
  log.appendChild(step);
  step.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  state.calcHintIdx++;

  if (state.calcHintIdx >= calcHints.length) {
    $('btn-next-calc-hint').classList.add('hidden');
    $('btn-back-to-answer').classList.remove('hidden');
  }
}

function handleTryAgain() {
  if (state.wrongContext === 'derivative') {
    goToScreen('screen-derivative');
  } else {

    const inp = $('answer-input');
    if (inp) inp.value = '';
    hideErr('answer-error');
    goToScreen('screen-answer');
  }
}

function handleShowSteps() {
  if (state.wrongContext === 'derivative') {
    loadAndShowDerivHints();
  } else {
    loadAndShowCalcHints();
  }
}

function restartApp() {

  state.lhsName = '';
  state.varNames = [];
  state.powers = {};
  state.derivHints = [];
  state.derivHintIdx = 0;
  state.calcHints = [];
  state.calcHintIdx = 0;
  state.wrongContext = '';

  const eqInp = $('eq-input');
  if (eqInp) eqInp.value = '';
  const ansInp = $('answer-input');
  if (ansInp) ansInp.value = '';

  hideErr('eq-error');
  hideErr('deriv-error');
  hideErr('errors-error');
  hideErr('answer-error');

  setProgressStep(1);
  goToScreen('screen-equation');
}

document.addEventListener('DOMContentLoaded', () => {
  setProgressStep(1);

  const inp = $('eq-input');
  if (inp) inp.focus();
});
