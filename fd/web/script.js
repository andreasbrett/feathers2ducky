"use strict";

function E(id) {
	return document.getElementById(id);
}

function fetchPayloads() {
	let xhr = new XMLHttpRequest();
	xhr.open("GET", "/api/fetchPayloads");
	xhr.responseType = "";

	xhr.onreadystatechange = () => {
		if (xhr.status == 200 && xhr.readyState == 4) {
			const response = JSON.parse(xhr.responseText).sort();
			let eList = E("payloadList");
			response.forEach((payload) => {
				let eListItem = document.createElement("li");
				let eLink = document.createElement("a");
				eLink.setAttribute("href", "#");
				eLink.setAttribute(
					"onclick",
					"loadPayload('" + payload + "');"
				);
				eLink.innerText = payload;

				eListItem.appendChild(eLink);
				eList.appendChild(eListItem);
			});

			document.body.style.cursor = "default";
		}
	};

	document.body.style.cursor = "progress";
	xhr.send();
}

function fetchStatistics() {
	let xhr = new XMLHttpRequest();
	xhr.open("GET", "/api/statistics");
	xhr.responseType = "";

	xhr.onreadystatechange = () => {
		if (xhr.status == 200 && xhr.readyState == 4) {
			const response = JSON.parse(xhr.responseText);
			E("board_name").innerText = response.board.name;
			E("chip_name").innerText = response.board.chip;
			E("circuitpython_version").innerText =
				response.board.circuitpython_version;
			E("circuitpython_version_full").innerText =
				response.board.circuitpython_version_full;

			const s = response.storage;
			E("storage_total").innerText =
				s.absolute.total + " " + s.absolute.unit_of_measurement;
			E("storage_used").innerText =
				s.absolute.used + " " + s.absolute.unit_of_measurement;
			E("storage_used_percentage").innerText =
				s.relative.used + s.relative.unit_of_measurement;
			E("storage_available").innerText =
				s.absolute.available + " " + s.absolute.unit_of_measurement;
			E("storage_available_percentage").innerText =
				s.relative.available + s.relative.unit_of_measurement;

			const m = response.memory;
			E("memory_total").innerText =
				m.absolute.total + " " + m.absolute.unit_of_measurement;
			E("memory_used").innerText =
				m.absolute.used + " " + m.absolute.unit_of_measurement;
			E("memory_used_percentage").innerText =
				m.relative.used + m.relative.unit_of_measurement;
			E("memory_available").innerText =
				m.absolute.available + " " + m.absolute.unit_of_measurement;
			E("memory_available_percentage").innerText =
				m.relative.available + m.relative.unit_of_measurement;

			document.body.style.cursor = "default";
		}
	};

	document.body.style.cursor = "progress";
	xhr.send();
}

function loadPayload(filename) {
	let xhr = new XMLHttpRequest();
	xhr.open("GET", "/api/loadPayload?file=" + filename);
	xhr.responseType = "";

	xhr.onreadystatechange = () => {
		if (xhr.status == 200 && xhr.readyState == 4) {
			const response = JSON.parse(xhr.responseText);
			let eCode = E("payloadCode");
			eCode.value = response.payload;
			let eFilename = E("payloadFilename");
			eFilename.innerText = "file: " + filename;
			eFilename.setAttribute("class", "notification background_gray");

			document.body.style.cursor = "default";
		}
	};

	document.body.style.cursor = "progress";
	xhr.send();
}

function runPayload() {
	let xhr = new XMLHttpRequest();
	xhr.open("POST", "/api/runPayload", true);
	xhr.responseType = "";
	xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

	xhr.onreadystatechange = () => {
		if (xhr.status == 200 && xhr.readyState == 4) {
			const response = JSON.parse(xhr.responseText);

			let eResult = E("payloadResult");
			let eNotification = E("payloadNotification");
			eResult.value = response.result;
			eNotification.innerText = response.notification;
			eNotification.setAttribute(
				"class",
				"notification background_green"
			);

			const eCode = E("payloadCode");
			document.body.style.cursor = "default";
			eCode.disabled = false;
			eResult.disabled = false;
		}
	};

	const eCode = E("payloadCode");
	const eResult = E("payloadResult");
	const postParams = "payload=" + eCode.value;

	document.body.style.cursor = "progress";
	eCode.disabled = true;
	eResult.value = "";
	eResult.disabled = true;
	xhr.send(postParams);
}

function newPayload() {
	E("payloadCode").value = "";
	E("payloadResult").value = "";

	let eFilename = E("payloadFilename");
	eFilename.innerText = "";
	eFilename.setAttribute("class", "");

	let eNotification = E("payloadNotification");
	eNotification.innerText = "";
	eNotification.setAttribute("class", "");
}

function savePayload() {
	const eFilename = E("payloadFilename");
	if (eFilename.innerText === "") {
		eFilename.innerText = window.prompt("Enter filename: ");
	}

	let xhr = new XMLHttpRequest();
	xhr.open("POST", "/api/savePayload", true);
	xhr.responseType = "";
	xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

	xhr.onreadystatechange = () => {
		if (xhr.status == 200 && xhr.readyState == 4) {
			const response = JSON.parse(xhr.responseText);

			let eNotification = E("payloadNotification");
			eNotification.innerText = response.notification;
			if (response.result === "success") {
				eNotification.setAttribute(
					"class",
					"notification background_green"
				);
			} else {
				eNotification.setAttribute(
					"class",
					"notification background_red"
				);
			}

			const eCode = E("payloadCode");
			document.body.style.cursor = "default";
			eCode.disabled = false;
		}
	};

	const eCode = E("payloadCode");
	const eNotification = E("payloadNotification");
	const postParams =
		"filename=" + eFilename.innerText + "&payload=" + eCode.value;

	document.body.style.cursor = "progress";
	eCode.disabled = true;
	eNotification.innerText = "";
	eNotification.setAttribute("class", "");
	xhr.send(postParams);
}

function init() {
	fetchPayloads();
	fetchStatistics();
}
