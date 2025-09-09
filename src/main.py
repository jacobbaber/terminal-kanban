"""Main entry point for terminal Kanban.

Uses internal key 'todo' while rendering header 'TO DO'.
"""
from board import Board
from storage import Storage
from cli import CLI


def main():
    tasks = Storage.load_tasks()
    board = Board(tasks)
    cli = CLI(board)
    cli.run()

if __name__ == "__main__":
    main()