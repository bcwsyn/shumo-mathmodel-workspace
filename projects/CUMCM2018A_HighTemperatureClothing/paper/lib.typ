#let academic-table(caption, columns, header, body, cell-align: center) = {
  let col-count = header.len()
  let body-rows = calc.floor(body.len() / col-count)
  figure(
    table(
      columns: columns,
      align: cell-align,
      stroke: none,
      inset: (x: 0.35em, y: 0.48em),
      table.hline(y: 0, stroke: 0.8pt),
      table.header(..header.map(strong)),
      table.hline(y: 1, stroke: 0.5pt),
      ..body,
      table.hline(y: body-rows + 1, stroke: 0.8pt),
    ),
    caption: caption,
  )
}
