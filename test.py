#!/usr/bin/env python3
import backend

E = backend.editor_state('garbage.txt')
E.init_gui()
E.create_cursor(0)
E.G.launch()
E.create_cursor( 1, 0, 1 )
