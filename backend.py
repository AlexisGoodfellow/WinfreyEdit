class editor_state:
    def __init__(self, filename=''):
        self.fname = filename
        self.cx = 0
        self.cy = 0
        try:
            with open(filename) as f:
                self.rows = f.read().split('\n')
        except FileNotFoundError:
            self.rows = []
        self.numrows = len(self.rows)
        for i in range(self.numrows - 1):
            self.rows[i] += '\n'

    def move_cursor(self, direction):
        if direction == 'left':
            self.cx -= 1
        elif direction == 'right':
            self.cx += 1
        elif direction == 'down':
            self.cy += 1
        else:
            self.cy -= 1

    def insert_char(self, c):
        row = self.cy
        col = self.cx
        r = self.rows[row]

        if c == '\n':
            self.rows[row] = r[:col] + c
            self.rows.insert(row + 1, r[col:])
        else:
            self.rows[row] = r[:col] + c + r[col:]

    def remove_char(self):
        row = self.cy
        col = self.cx
        r = self.rows[row]

        if r[col] == '\n':
            self.rows[row] = r[:col] + self.rows[row + 1]
            self.rows.pop(row + 1)
        else:
            self.rows[row] = r[:col] + r[col + 1:]

    def write(self, filename=''):
        if filename == '':
            filename = self.fname
        try:
            if filename != '':
                with open(filename) as f:
                    f.write(''.join(self.rows))
        except FileNotFoundError:
            pass
