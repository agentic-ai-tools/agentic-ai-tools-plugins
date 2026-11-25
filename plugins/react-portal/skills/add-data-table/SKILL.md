---
name: add-data-table
description: Add a data table that follows the number and missing-figure rules. Use when a page shows figures, money, metrics, or scenarios in a table.
---

# Add a data table

1. Use a real `table`. Every header cell is a `th` with a `scope`.
2. Numeric columns are right-aligned and use `tabular-nums`. The header row sticks when the table scrolls.
3. Format with `Intl.NumberFormat` in the record's currency and the person's locale. Show the unit or currency on every figure or in its column header. Negative values use a minus sign, not colour alone. Percentages show one decimal place unless the source is more precise.
4. A figure that was not computed shows an em dash and the reason in text, such as "Not computed: missing discount rate". Never show 0 for missing.
5. Below 560px the table scrolls horizontally in its own region with the first column fixed. It does not reflow into cards.
6. Scenarios (best, expected, worst) sit side by side with the same rows. A chart of the same data always has this table next to it or one switch away.
7. Test the formatting, the missing-figure text, and the header scopes.
