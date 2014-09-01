# Snakelisp

The snakelisp is a lisp dialect by Henri Tuhola. It is a study language to explore binary list processing.

Code sample:

 ![Factorial in lisp-editor](examples/factorial.png)

Binary list processing uses "binary lists" instead of plain text files to store source code and data. The lists are read and modified with structure editors, such as [lisp-editor](https://www.youtube.com/watch?v=-AZbteER_Ho).

The author expects such environment to be more powerful than lisp, and more readable than python. Without readability issues, list processing environments are easier to understand and work with and provide better understanding about the programs written in them, with faster development cycles.

The downside is that nearly every text based tool ceases functioning with binary lists.

## Syntax

The language is using a variation of the list notation, common for lisp family of the languages. The B-expression may be a list, symbol, marker or a binary blob. Every B-expression may hold a label or an uid -string.

In the primary representation list is a box, which encloses it's elements, that appear in order: from left to right, from top to bottom. A "cr" -labeled marker may be interpreted as a line break, which can be filtered away before evaluating the form.

### Comments

Comments go to a separate layer -file, which matches with an uid -string in each element. The layer is broken into individual pieces that are laid aside the source file. The comment layer is optional.

The layer file's topmost list is labelled as `comments`. It consists of liss, each starting with an uid symbol/string. The body of that list is part of the comment.

### Numbers

Symbols beginning with a number, without a label will be interpreted as numbers.

    1234
    3x12012
    5.2

This notation is maintained, although it is not required for an implementation to implement this specific interpretation for symbols.

### Strings

Strings are symbols that have `string` -label. No escape character notation is required. The visual attempts to represent unprintable characters.

## Lexical scope

The snakelisp is lexically scoped. Every function defines a boundary. Inside the boundary one is free to bind new values with `let` -list. Variables in higher scope can be set with `set` -labelled list.

## Continuation passing as evaluation strategy

The snakelisp is compiling itself into continuation passing style as the intermediary form. The current compilation strategy follows the Cheney on the M.T.A. -paper. It is not suitable for interactive evaluation, so it will be supplied with an interpreter later on.
