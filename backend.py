import gui

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
        self.G = gui.MultiCursorGui(self.rows, self.insert_char, self.move_cursor)
        for i in range(self.numrows - 1):
            self.rows[i] += '\n'

    def move_cursor_in_row( self, x ):
        self.cx = x;
        self.G.change_line( self.cy, self.rows[self.cy][:-1], [self.cx])

    def move_cursor(self, direction):
        """ Move the cursor sanely, handling all bounds checking. """
        # Move left unless at beginning of line
        if direction == 'left' and self.cx != 0:
            self.move_cursor_in_row( self.cx - 1 );
        # Move right unless at end of line
        elif direction == 'right' and self.rows[self.cy][self.cx] != '\n':
            self.move_cursor_in_row( self.cx + 1 );
        # Move down, accounting for line length differences
        # and never moving beyond the last line of the file
        elif direction == 'down' and self.cy < len(self.rows) - 2:
            curr_line_len = len(self.rows[self.cy])
            self.cy += 1
            next_line_len = len(self.rows[self.cy])
            if next_line_len < curr_line_len and next_line_len - 1 < self.cx: 
                self.cx = next_line_len - 1
            self.G.change_line (self.cy - 1, self.rows[self.cy - 1][:-1], [])
            self.G.change_line (self.cy, self.rows[self.cy][:-1], [self.cx])
        # Move up, accounting for line length differences
        # and never moving before the first line of the file
        elif direction == 'up' and self.cy > 0:
            curr_line_len = len(self.rows[self.cy])
            self.cy -= 1
            next_line_len = len(self.rows[self.cy])
            if next_line_len < curr_line_len and next_line_len - 1 < self.cx: 
                self.cx = next_line_len - 1
            self.G.change_line (self.cy + 1, self.rows[self.cy + 1][:-1], [])
            self.G.change_line (self.cy, self.rows[self.cy][:-1], [self.cx])
        elif direction == 'backspace':
            if self.cx > 0:
                self.move_cursor('left')
                self.remove_char()
            else:
                self.move_cursor('up')
                self.move_cursor_in_row(len(self.rows[self.cy]) - 1)
                self.rows[self.cy] = self.rows[self.cy][:-1]
                self.rows[self.cy] += self.rows[self.cy+1]
                self.rows.pop( self.cy + 1 )
                self.G.delete_line( self.cy + 1 )
                self.G.change_line( self.cy, self.rows[self.cy][:-1], [self.cx] )
        elif direction == 'delete':# and (self.cy < self.numrows or self.rows[self.cy][self.cx] != '\n'):
            if self.cy == self.numrows - 2:
                if self.rows[self.cy][self.cx] != '\n':
                    self.remove_char()
            else:
                self.remove_char()
        elif direction == 'enter':
            self.insert_char('\n')

    def insert_char(self, c):
        row = self.cy
        col = self.cx
        r = self.rows[row]

        if c == '\n':
            self.rows[row] = r[:col] + c
            self.rows.insert(row + 1, r[col:])
            self.G.add_line(row, r[col:], [])
            self.G.change_line(row, r[:col], [])
            self.move_cursor('down')
            self.move_cursor_in_row( 0 );
        else:
            self.rows[row] = r[:col] + c + r[col:]
            self.G.change_line(row, self.rows[row][:-1], [col])
            self.move_cursor('right')

    def remove_char(self):
        row = self.cy
        col = self.cx
        r = self.rows[row]

        if r[col] == '\n':
            self.rows[row] = r[:col] + self.rows[row + 1]
            self.rows.pop(row + 1)
            self.G.delete_line(row + 1)
            self.G.change_line(row, self.rows[row][:-1], [col])
        else:
            self.rows[row] = r[:col] + r[col + 1:]
            self.G.change_line(row, self.rows[row][:-1], [col])

    def write(self, filename=''):
        if filename == '':
            filename = self.fname
        try:
            if filename != '':
                with open(filename) as f:
                    f.write(''.join(self.rows))
        except FileNotFoundError:
            pass
