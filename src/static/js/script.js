async function loadTrajectory() {
  const url = "/data-endpoint?session_id=" + encodeURIComponent(SESSION_ID);
  let resp;
  try {
    resp = await fetch(url);
  } catch (e) {
    console.error("Failed to fetch trajectory data:", e);
    return;
  }
  if (!resp.ok) {
    console.error("Trajectory data endpoint returned", resp.status);
    return;
  }

  const text = await resp.text();
  const lines = text.trim().split("\n");
  if (lines.length < 2) return;

  const header = lines[0].split(",");
  const rows = lines.slice(1).map(function (line) {
    const vals = line.split(",");
    const row = {};
    header.forEach(function (h, i) { row[h] = vals[i]; });
    return row;
  });

  function unpack(rows, key) {
    return rows.map(function (row) { return row[key]; });
  }

  var x = unpack(rows, "x");
  var y = unpack(rows, "y");
  var z = unpack(rows, "z");
  var c = unpack(rows, "timestamp");

  var config = { responsive: true };

  var layout = {
    margin: { l: 0, r: 0, b: 0, t: 0, pad: 0 },
    scene: {
      aspectmode: "data",
      camera: {
        eye: { x: 5, y: 5, z: 5 },
        center: { x: 0, y: 0, z: 0 },
      },
    },
    autosize: true,
  };

  Plotly.newPlot(
    "myDiv",
    [
      {
        type: "scatter3d",
        mode: "lines",
        x: x,
        y: y,
        z: z,
        opacity: 1,
        line: {
          width: 6,
          color: c,
          reversescale: false,
        },
      },
    ],
    layout,
    config,
  );
}

loadTrajectory();
