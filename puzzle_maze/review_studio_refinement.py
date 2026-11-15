"""Compatibility capture command for the current production workshop."""
import argparse
from puzzle_maze.review_workshop import generate as generate_refinement
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='/tmp/studio-refinement')
    generate_refinement(p.parse_args().output)
