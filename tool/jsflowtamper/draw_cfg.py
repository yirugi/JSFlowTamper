#!/usr/local/bin/python

import json
from graphviz import Digraph

NODETYPE = ['var-decl', 'func-decl', 'do-while', 'while', 'for', 'for-in', 'for-of', 'block', 'switch', 'exp', 'empty', 'sloppy-block-func', 'if', 'continue', 'break',
            'return', 'with', 'try-catch', 'try-finally', 'debugger', 'init-class', 'reg-exp', 'object', 'array', 'assign', 'await', 'binary-op', 'nary', 'call', 'callnew',
            'call-runtime', 'class', 'compare', 'compound-assign', 'conditional', 'count', 'do-express', 'empty-parenth', 'func', 'get-it', 'get-tmp-obj', 'import-call',
            'literal', 'native-func', 'prop.', 'resolve-prop', 'rewritable', 'spread', 'super-call', 'super-prop', 'this', 'throw', 'unary', 'var-proxy', 'yield', 'yield-star']

def draw_cfg(data, sbb_id = None, cds = None):

    g = Digraph('G', filename='output.gv', node_attr={'shape':'plaintext'})

    for sbb in data['sbbs'][:-1]:
        id = sbb['id']

        highlight = ''

        if sbb_id is None:
            for call in data['trace_calls']:
                if id == call['id']:
                    highlight = 'BGCOLOR="yellow"'
                    break
        else:
            if id == sbb_id:
                highlight = 'BGCOLOR="yellow"'
            elif id in cds:
                highlight = 'BGCOLOR="green"'

        # node
        stmt_str = ''
        for stmt in sbb['statements']:

            node_type = NODETYPE[int(stmt['node_type'])]
            str = stmt['position'] + "\t " + node_type

            if highlight != '':
                for call in data['trace_calls']:
                    if stmt['position'] == call['pos']:
                        str = '<B>' + str + '</B>'
                        break

            stmt_str += str + '<br/>'

        node_html = '''<
        <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
            <tr>
                <td port="id" %s>%s</td>
            </tr>
            <tr>
                <TD port="data" BALIGN="LEFT">%s</TD>
            </tr>
        </TABLE>
        >'''%(highlight, id, stmt_str)

        g.node(id, node_html)

        # edge
        if sbb['control'] == '1': #goto
            g.edge(id + ':data', sbb['successors'][0] + ":id", constraint='true', style='dashed')
        elif sbb['control'] in ['2', '3']: #if / ternary
            g.edge(id + ':data', sbb['successors'][0] + ":id", label='T')
            g.edge(id + ':data', sbb['successors'][1] + ":id", label='F')
        elif sbb['control'] == '6': #try-catch
            g.edge(id + ':data', sbb['successors'][0] + ":id")
            g.edge(id + ':data', sbb['successors'][1] + ":id", label='catch', style='dotted')
        else:
            for succ in sbb['successors']:
                g.edge(id + ':data', succ + ":id")

    # end node
    lastid = data['sbbs'][-1]['id']
    g.node(lastid, 'END', shape='circle')

    for i, line in enumerate(g.body):
        if lastid + ':id' in line:
            g.body[i] = line.replace(lastid + ':id', lastid)


    g.view()