/**
 * This file will serve as the "View + ViewController".
 * wasm stuff are all "Controller + Model"
*/

import * as wasm from "web";

// referencable objects that i care about
const copyLink = document.getElementById('sharing-link');
const fromDateField = document.getElementById('from-date');
const toDateField = document.getElementById('to-date');
const fromDateToday = document.getElementById('from-date-today');
const toDateToday = document.getElementById('to-date-today');
const statusText = document.getElementById('status');
const fromCommitText = document.getElementById('from-commit');
const toCommitText = document.getElementById('to-commit');
const tableParent = document.getElementById('table-parent');

// set date/time to query params (if applicable)
const urlParams = new URLSearchParams(window.location.search);
const fromDate = urlParams.get('fromDate');
const toDate = urlParams.get('toDate');
const dateNow = (new Date()).toISOString().split('.')[0];

const tableHeaders = "<table id=\"resource-table\"><tr><th>Resource</th><th>Status</th><th>Previous State</th><th>Current State</th></tr>";
const tableFooter = "</table>";

const commitURL = "https://github.com/neuro-arg/arg-monitoring/commit/";

// functions and stuff
const updateTable = async () => {
  const lhsDate = fromDateField.value;
  const rhsDate = toDateField.value;
  const result = await wasm.compare_cache_on_dates(lhsDate, rhsDate);

  const lhsState = result.lhs_state;
  const rhsState = result.rhs_state;
  const statusMapping = result.match_tuples;
  const lhsCommit = result.lhs_commit;
  const rhsCommit = result.rhs_commit;

  fromCommitText.innerText = lhsCommit;
  toCommitText.innerText = rhsCommit;

  fromCommitText.href = commitURL + lhsCommit;
  toCommitText.href = commitURL + rhsCommit;

  // both states are expected to have all keys. Even if they aren't
  // in the original JSON, the WASM should have returned them as
  // undefined
  let newInnerHTML = tableHeaders;
  for (const key of Object.keys(lhsState)) {
    const templateStr = `<tr>
                         <td>${key}</td>
                         <td>${statusMapping.get(key) ? "Matches" : "Does not match"}</td>
                         <td>${JSON.stringify(lhsState[key], null, true)}</td>
                         <td>${JSON.stringify(rhsState[key], null, true)}</td>
                         </tr>`;
    newInnerHTML += templateStr;
  }
  newInnerHTML += tableFooter;
  tableParent.innerHTML = newInnerHTML;

  // NOTE: it seems not all browsers have Iterator.prototype,
  // so I use a primitive method
  let res = true;
  for (const val of statusMapping.values()) {
    if (!val) {
      res = false;
      break
    }
  }
  statusText.innerText = res ? "Full Match" : "Some does not match";
}

const updateHistory = () => {
  history.pushState(null, '', window.location.pathname + '?' + urlParams.toString())
}

const updateDateFields = (urlField, newDate) => {
  urlParams.set(urlField, newDate);
  updateHistory();
  updateTable();
}


if (!('URLSearchParams' in window)) {
  alert("Please use a less ancient browser");
}

if (fromDate && fromDate !== 'today') {
  fromDateField.value = new Date(fromDate).toISOString().split('.')[0];
} else {
  urlParams.set('fromDate', 'today');
  fromDateField.value = dateNow;
}

if (toDate && toDate !== 'today') {
  toDateField.value = new Date(toDate).toISOString().split('.')[0];
} else {
  urlParams.set('toDate', 'today');
  toDateField.value = dateNow;
}

// first updates
updateHistory();
updateTable();


// listeners and stuff
copyLink.addEventListener('click', () => {
  navigator.clipboard.writeText(window.location);
})

fromDateField.addEventListener('change', e => {
  updateDateFields('fromDate', e.target.value);
})

toDateField.addEventListener('change', e => {
  updateDateFields('toDate', e.target.value);
})

fromDateToday.addEventListener('click', () => {
  fromDateField.value = dateNow;
  updateDateFields('fromDate', 'today');
})

toDateToday.addEventListener('click', () => {
  toDateField.value = dateNow;
  updateDateFields('toDate', 'today');
})
