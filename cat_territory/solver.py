"""Row-by-row constraint search for one cat per row, column and region."""


class TerritorySolver:
    @staticmethod
    def solutions(regions, limit=2, cats=(), marks=()):
        size = len(regions)
        found = []
        fixed = {}
        blocked = set(marks)
        for x,y in cats:
            if not (0 <= x < size and 0 <= y < size) or y in fixed or (x,y) in blocked:
                return []
            fixed[y] = x

        def visit(row, columns, colors, chosen):
            if len(found) >= limit:
                return
            if row == size:
                found.append(tuple(chosen))
                return
            for column in ([fixed[row]] if row in fixed else range(size)):
                if (column,row) in blocked:
                    continue
                color = regions[row][column]
                if column in columns or color in colors:
                    continue
                if chosen and abs(column-chosen[-1]) <= 1:
                    continue
                visit(row+1, columns | {column}, colors | {color}, chosen+[column])
        visit(0, set(), set(), [])
        return found
