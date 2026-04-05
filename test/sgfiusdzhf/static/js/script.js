d3.csv("/data-endpoint", function (err, rows) {
  function unpack(rows, key) {
    return rows.map(function (row) {
      return row[key];
    });
  }

  var config = {
    responsive: true,
  };

  var x = unpack(rows, "x");
  var y = unpack(rows, "y");
  var z = unpack(rows, "z");
  var c = unpack(rows, "color");

  const layout = {
    margin: {
      l: 0,
      r: 0,
      b: 0,
      t: 0,
      pad: 0,
    },
    scene: {
      aspectmode: "data", // Start with cube to see if it fits, then switch to 'data'
      camera: {
        eye: { x: 5, y: 5, z: 5 }, // Move back slightly
        center: { x: 0, y: 0, z: 0 }, // Ensure it's centered
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
});
