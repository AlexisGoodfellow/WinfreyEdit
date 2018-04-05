import gui

class editor_state:
    def __init__(self, filename=''):
        self.fname = filename

        self.cursors = {}
        self.my_cursor = 0;

        try:
            with open(filename) as f:
                self.rows = f.read().split('\n')
        except FileNotFoundError:
            self.rows = []
        self.numrows = len(self.rows)
        self.G = gui.MultiCursorGui( self.rows, self.insert_my_char, self.move_my_cursor, self.interrupt )
        for i in range(self.numrows - 1):
            self.rows[i] += '\n'

    def interrupt( self ):
        pass

    def update_line( self, line ):
        self.G.change_line( line, self.rows[line][:-1], [self.cursors[key]["cx"] for key in self.cursors if self.cursors[key]["cy"] == line])

    def create_cursor( self, cid, x=0, y=0):
        self.cursors[cid] = {"cx": x, "cy": y};
        self.update_line( self.cursors[cid]["cy"] )

    def remove_cursor( self, cid ):
        line = self.cursors[cid]["cy"]
        del self.cursors[cid]
        self.update_line( line )

    def move_cursor_in_row( self, cid, x ):
        self.cursors[cid]["cx"] = x;
        self.update_line( self.cursors[cid]["cy"] )

    def insert_my_char( self, char ):
        self.insert_char( self.my_cursor, char )

    def move_my_cursor( self, direction ):
        self.move_cursor( self.my_cursor, direction )

    def move_cursor(self, cid, direction):
        """ Move the cursor sanely, handling all bounds checking. """

        cursor = self.cursors[cid];

        # Move left unless at beginning of line
        if direction == 'left' and cursor["cx"] != 0:
            self.move_cursor_in_row( cid, cursor["cx"] - 1 );
        # Move right unless at end of line
        elif direction == 'right' and self.rows[cursor["cy"]][cursor["cx"]] != '\n':
            self.move_cursor_in_row( cid, cursor["cx"] + 1 );
        # Move down, accounting for line length differences
        # and never moving beyond the last line of the file
        elif direction == 'down' and cursor["cy"] < len(self.rows) - 2:
            curr_line_len = len(self.rows[cursor["cy"]])
            self.cursors[cid]["cy"] += 1
            next_line_len = len(self.rows[cursor["cy"]])
            if next_line_len < curr_line_len and next_line_len - 1 < cursor["cx"]: 
                self.cursors[cid]["cx"] = next_line_len - 1
            self.update_line( cursor["cy"] - 1 )
            self.update_line( cursor["cy"] )
        # Move up, accounting for line length differences
        # and never moving before the first line of the file
        elif direction == 'up' and cursor["cy"] > 0:
            curr_line_len = len(self.rows[cursor["cy"]])
            self.cursors[cid]["cy"] -= 1
            next_line_len = len(self.rows[cursor["cy"]])
            if next_line_len < curr_line_len and next_line_len - 1 < cursor["cx"]: 
                self.cursors[cid]["cx"] = next_line_len - 1
            self.update_line( cursor["cy"] + 1 )
            self.update_line( cursor["cy"] )
        # delete character in front of cursor
        elif direction == 'backspace':
            if cursor["cx"] > 0:
                self.move_cursor( cid, 'left' )
                self.remove_char( cid )
            elif cursor["cy"] != 0:
                self.move_cursor( cid, 'up' )
                self.move_cursor_in_row( cid, len(self.rows[cursor["cy"]]) - 1)
                self.rows[cursor["cy"]] = self.rows[cursor["cy"]][:-1]
                self.rows[cursor["cy"]] += self.rows[cursor["cy"]+1]
                self.rows.pop( cursor["cy"] + 1 )
                self.G.delete_line( cursor["cy"] + 1 )
                self.update_line( cursor["cy"] )
        # delete character under cursor
        elif direction == 'delete':
            if cursor["cy"] == self.numrows - 2:
                if self.rows[cursor["cy"]][cursor["cx"]] != '\n':
                    self.remove_char( cid )
            else:
                self.remove_char( cid )
        # 
        elif direction == 'enter':
            self.insert_char( cid, '\n' )

    def insert_char(self, cid, c):
        row = self.cursors[cid]["cy"]
        col = self.cursors[cid]["cx"]
        r = self.rows[row]

        if c == '\n':
            self.rows[row] = r[:col] + c
            self.rows.insert(row + 1, r[col:])
            self.G.add_line(row, r[col:], [])
            self.update_line( row )
            self.move_cursor(cid, 'down')
            self.move_cursor_in_row(cid, 0)
        else:
            self.rows[row] = r[:col] + c + r[col:]
            self.update_line( row )
            self.move_cursor(cid, 'right')

    def remove_char(self, cid):
        row = self.cursors[cid]["cy"]
        col = self.cursors[cid]["cx"]
        r = self.rows[row]

        if r[col] == '\n':
            self.rows[row] = r[:col] + self.rows[row + 1]
            self.rows.pop(row + 1)
            self.G.delete_line(row + 1)
            self.update_line( row )
        else:
            self.rows[row] = r[:col] + r[col + 1:]
            self.update_line( row )

    def write(self, filename=''):
        if filename == '':
            filename = self.fname
        try:
            if filename != '':
                with open(filename, 'w') as f:
                    f.write(''.join(self.rows))
        except FileNotFoundError:
            pass
