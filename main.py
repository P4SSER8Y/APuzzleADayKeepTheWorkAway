#!/usr/bin/env python3
import click
import yaml
import re
import tabulate
import copy
import datetime
import logging
import progressbar
import functools
import os

tabulate.PRESERVE_WHITESPACE = True
progressbar.streams.wrap_stderr()
logging.basicConfig(level=logging.INFO)


def fancy_board(pattern):
    return tabulate.tabulate(pattern, tablefmt='fancy_grid')


def fancy(table, codes):
    table = copy.deepcopy(table)
    grid_width = 1
    for line in table:
        grid_width = max(grid_width, max([len(x) for x in line]))
    for line in table:
        for i in range(len(line)):
            line[i] = f"{line[i]: ^{grid_width}}"
    contents = tabulate.tabulate(table, tablefmt="fancy_grid").split('\n')
    for code in codes:
        expended_code = f"{code: ^{grid_width}}"
        for i in range(1, len(contents), 2):
            for match in re.finditer(r"(?<={0})\s*│\s*(?={0})".format(expended_code), contents[i]):
                contents[i] = contents[i][:match.start()] + '█' * \
                    (match.end() - match.start()) + contents[i][match.end():]
        for i in range(1, len(contents) - 2, 2):
            curr = [(x.start(), x.end()) for x in re.finditer(
                r"(?<=[\s█]){}(?=[\s█])".format(expended_code), contents[i])]
            if len(curr) > 0:
                next = [(x.start(), x.end()) for x in re.finditer(
                    r"(?<=[\s█]){}(?=[\s█])".format(expended_code), contents[i + 2])]
                for p in curr:
                    if p in next:
                        contents[i + 1] = contents[i + 1][:p[0]] + \
                            '█' * (p[1] - p[0]) + contents[i + 1][p[1]:]
        for i in range(1, len(contents), 2):
            contents[i] = re.sub(expended_code, '█' * grid_width, contents[i])
    return '\n'.join(contents)


def load_board(pattern, groups):
    board = []
    pattern = [x for x in pattern if len(x) > 0]
    height = len(pattern)
    g = functools.reduce(lambda x, y: x + y, groups, [])
    for line in pattern:
        grids = re.split(r"\s+", line.strip())
        for i in range(len(grids)):
            if not grids[i] in g:
                grids[i] = None
        board.append(grids)
    width = max([len(x) for x in board])
    for line in board:
        while len(line) < width:
            line.append(None)
    return board


def load_tile(code, tile):
    def rotate(input):
        h = len(input)
        w = len(input[0])
        output = []
        for _ in range(len(input[0])):
            output.append([' ', ] * len(input))
        for x in range(h):
            for y in range(w):
                output[w - 1 - y][x] = input[x][y]
        return output

    def mirror(input):
        output = copy.deepcopy(input)
        for line in output:
            line.reverse()
        return output
    tiles = []
    # format base tile
    tile = [list(x.strip()) for x in tile if len(x) > 0]
    for line in tile:
        for i in range(len(line)):
            if line[i] == 'o':
                line[i] = code
            else:
                line[i] = None
    height = len(tile)
    width = max([len(x) for x in tile])
    for line in tile:
        while len(line) < width:
            line.append(None)
    # generate all possible rotate or mirror
    for _ in range(4):
        tiles.append(copy.deepcopy(tile))
        tile = rotate(tile)
    tile = mirror(tile)
    for _ in range(4):
        tiles.append(copy.deepcopy(tile))
        tile = rotate(tile)
    # remove dumplicate tiles
    ret = []
    for i in range(len(tiles)):
        flag = True
        for j in range(i - 1):
            if tiles[i] == tiles[j]:
                flag = False
                break
        if flag:
            ret.append(tiles[i])
    return ret


def is_placable(board, tile, x, y):
    for i in range(len(tile[0])):
        if tile[0][i]:
            y = y - i
            break
    if (y < 0) or (x + len(tile) > len(board)) or (y + len(tile[0]) > len(board[0])):
        return False
    for i in range(len(tile)):
        for j in range(len(tile[0])):
            if tile[i][j] and board[x + i][y + j]:
                return False
    return True


def place_tile(board, tile, x, y):
    for i in range(len(tile[0])):
        if tile[0][i]:
            y = y - i
            break
    for i in range(len(tile)):
        for j in range(len(tile[0])):
            if tile[i][j]:
                board[x + i][y + j] = tile[i][j]


def remove_tile(board, tile, x, y):
    for i in range(len(tile[0])):
        if tile[0][i]:
            y = y - i
            break
    for i in range(len(tile)):
        for j in range(len(tile[0])):
            if tile[i][j]:
                board[x + i][y + j] = None


def dfs(board, tiles, used, remain):
    if remain == 0:
        return [copy.deepcopy(board)]
    results = []
    x = 0
    y = 0
    flag = False
    for x in range(len(board)):
        for y in range(len(board[0])):
            if board[x][y] is None:
                flag = True
                break
        if flag:
            break
    for i in range(len(used)):
        if used[i]:
            continue
        used[i] = True
        for tile in tiles[i]:
            if is_placable(board, tile, x, y):
                place_tile(board, tile, x, y)
                results = results + dfs(board, tiles, used, remain - 1)
                remove_tile(board, tile, x, y)
        used[i] = False
    return results


def f(board, tiles, grids):
    board = copy.deepcopy(board)
    positions = []
    for grid in grids:
        flag = False
        for x in range(len(board)):
            for y in range(len(board[0])):
                if board[x][y] and (board[x][y].strip().lower() == grid.strip().lower()):
                    positions.append((x, y))
                    board[x][y] = None
                    flag = True
                    break
            if flag:
                break
        if not flag:
            return
    for x in range(len(board)):
        for y in range(len(board[0])):
            if board[x][y]:
                board[x][y] = None
            else:
                board[x][y] = ' '
    for i in range(len(positions)):
        board[positions[i][0]][positions[i][1]] = grids[i]
    results = dfs(board, tiles, [False] * len(tiles), len(tiles))
    return results


def search_all(board, tiles, groups):
    statistic = []
    count = 1
    pbar = progressbar.ProgressBar(max_value=functools.reduce(
        lambda v, item: v * len(item), groups, 1))

    def iter(grids, index):
        if index >= len(groups):
            nonlocal count
            pbar.update(count)
            count = count + 1
            start = datetime.datetime.now()
            results = f(board, tiles, grids)
            end = datetime.datetime.now()
            logging.info("{}: {} results, used {:0.3f}s".format(
                "-".join(grids), len(results), (end - start).total_seconds()))
            pbar.update(count)
            statistic.append(("-".join(grids), results))
            return
        for item in groups[index]:
            iter(grids + [item], index + 1)
    iter([], 0)
    return statistic


def generate_md_single(board, grids, results, codes, used_time):
    grid_str = "-".join(grids)
    os.makedirs("results", exist_ok=True)
    with open(f"results/{grid_str}.md", "w") as f:
        content = [
            f"Solutions for {grid_str}",
            f"{'':=^20}",
            f"+ search time: {used_time:0.3f}s",
            f"+ solution count: {len(results)}",
            "+ board:",
            "~~~",
            "",
        ]
        f.write('\n'.join(content))
        f.write(fancy_board(board))
        content = ["", "~~~", "", ""]
        f.write('\n'.join(content))
        for i in range(len(results)):
            content = [
                f"Solution #{i + 1}",
                f"{'':-^20}",
                "~~~",
                fancy(results[i], codes),
                "~~~",
                "",
                "",
            ]
            f.write('\n'.join(content))


@click.command()
@click.argument('config_file', type=click.File('r'))
@click.argument('grids', nargs=-1)
def main(config_file, grids):
    """
    find all solutions for Calendar Puzzzle, in order to save time for work\n
        ./main.py month_day.yml                     # find all solutions\n
        ./main.py month_day.yml JUN 26\n
        ./main.py month_day_weekday.yml JUN 26 Sat\n
    """
    config = yaml.safe_load(config_file)
    board = load_board(config["board"], config["groups"])
    logging.info("original board: \n{}".format(fancy_board(board)))
    tiles = []
    for tile in config["tiles"]:
        tiles.append(load_tile(tile["code"], tile["shape"]))
    if grids:
        start = datetime.datetime.now()
        results = f(board, tiles, grids)
        end = datetime.datetime.now()
        logging.info("{}: {} results, used {:0.3f}s".format(
            "-".join(grids), len(results), (end - start).total_seconds()))
        generate_md_single(board, grids, results, [tile["code"] for tile in config["tiles"]], (end - start).total_seconds())
    else:
        start = datetime.datetime.now()
        results = search_all(board, tiles, config["groups"])
        end = datetime.datetime.now()
    return results


if __name__ == "__main__":
    results = main()
