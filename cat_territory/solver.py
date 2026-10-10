"""Row-by-row constraint search for one cat per row, column and region."""


class TerritorySolver:
    @staticmethod
    def solutions(regions, limit=2):
        size = len(regions)
        found = []

        def visit(row, columns, colors, chosen):
            if len(found) >= limit:
                return
            if row == size:
                found.append(tuple(chosen))
                return
            for column in range(size):
                color = regions[row][column]
                if column in columns or color in colors:
                    continue
                if chosen and abs(column-chosen[-1]) <= 1:
                    continue
                visit(row+1, columns | {column}, colors | {color}, chosen+[column])
        visit(0, set(), set(), [])
        return found
