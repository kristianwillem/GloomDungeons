import random
import uf


class Mutation:

    def __init__(self, all_rules, all_rooms, all_monsters, all_chests, min_size, max_size):
        self.all_rules = all_rules
        self.all_rooms = all_rooms
        self.all_monsters = all_monsters
        self.all_chests = all_chests
        self.min_size = min_size
        self.max_size = max_size

        self.rule_chance_base = 0.8
        self.chest_chance_base = 0.8
        self.monster_theme_bias = 2

    def mutate(self, dungeon):
        # use random(choices) to randomize this
        self.mutate_rules(dungeon)
        self.mutate_monsters(dungeon)
        self.mutate_environment(dungeon)
        self.mutate_treasure(dungeon)

        # While it is usually at another place, I've moved the map mutation to the bottom since it also mutates the
        # "Placement" attribute, which depends on all other attributes.
        self.mutate_map(dungeon)

    # for a more advanced (non-MVP) version:
    # gaussian distribution with the ideal as mean and a (variable) standard deviation.
    # every step, test the current value against the ideal value.

    def mutate_rules(self, dungeon):
        rule_chance = self.rule_chance_base
        dungeon.rules = set(())
        mutate_loop = True
        while mutate_loop:
            rule_test = random.random()
            if rule_test < rule_chance:
                new_rule = random.choice(self.all_rules)
                dungeon.rules.add(new_rule)
                rule_chance /= 2
            else:
                mutate_loop = False

    def mutate_monsters(self, dungeon):
        for monster in dungeon.monsters:
            old_monster = dungeon.monsters[monster]
            monster_type = old_monster[0]
            normal_amount = old_monster[1]
            elite_amount = old_monster[2]

            # create a list of monsters & themes for weighted random
            theme_weight = []
            for entry in self.all_monsters:
                if entry.theme == monster_type.theme:
                    theme_weight.append(self.monster_theme_bias)
                else:
                    theme_weight.append(1)
            new_monster_type = random.choices(self.all_monsters, theme_weight)[0]

            # add other necessary components. For the slightly more than MVP, use randomization for this.

            difficulty_ratio = monster_type.difficulty/new_monster_type.difficulty
            new_normal_amount = round(normal_amount * difficulty_ratio)
            new_elite_amount = round(elite_amount * difficulty_ratio)

            new_monster = [new_monster_type, new_normal_amount, new_elite_amount]
            dungeon.monsters[monster] = new_monster

    def mutate_environment(self, dungeon):
        # using gaussian to create a 95% chance that the new number will be between 0.5 and 1.5 times the original.
        environment_list = [dungeon.obstacles, dungeon.traps, dungeon.h_terrain, dungeon.d_terrain]
        for i in range(len(environment_list)):
            mu = environment_list[i]
            if mu == 0:
                sigma = 1
            else:
                sigma = mu/4
            new_entry = round(random.normalvariate(mu, sigma))
            environment_list[i] = abs(new_entry)
        dungeon.obstacles = environment_list[0]
        dungeon.traps = environment_list[1]
        dungeon.h_terrain = environment_list[2]
        dungeon.d_terrain = environment_list[3]

    def mutate_treasure(self, dungeon):
        # new amount of coins, similar to environment
        coin_amount = dungeon.coins
        mu = coin_amount
        if mu == 0:
            sigma = 1
        else:
            sigma = coin_amount/4
        new_coins = round(random.normalvariate(mu, sigma))
        dungeon.coins = abs(new_coins)

        # new treaure, similar to rules
        chest_chance = self.chest_chance_base
        dungeon.chests = []
        mutate_loop = True
        while mutate_loop:
            chest_test = random.random()
            if chest_test < chest_chance:
                new_chest = random.choice(self.all_chests)
                dungeon.chests.append(new_chest)
                chest_chance /= 2
            else:
                mutate_loop = False

    def mutate_map(self, dungeon):
        # room & connection randomization
        dungeon.rooms = []
        open_links = dict()
        size = 0
        mutate_loop = True
        while mutate_loop:
            # select random room
            new_room = random.choice(self.all_rooms)
            valid_room = True

            if not dungeon.rooms:
                dungeon.theme = new_room.theme
                new_connection = []
                new_rotation = 0
            else:
                # check if the room is available
                for other_room in dungeon.rooms:
                    if other_room == new_room:
                        valid_room = False

                # connect new room (all possible connections)
                chosen_connection = self.connect(open_links, new_room)
                old_room = chosen_connection[0]
                old_link = chosen_connection[1]
                new_link = chosen_connection[2]
                link_rotation = (old_link[3] - new_link[3] + 6)/2
                link_rotation += dungeon.rotation[old_room]
                link_rotation = link_rotation % 6
                if link_rotation < 0:
                    link_rotation += 6
                new_connection = [old_room, chosen_connection[1], new_room, new_link]
                new_rotation = link_rotation

                # check for validity (connections)
                if new_connection == 0:
                    valid_room = False

            if valid_room:
                size += new_room.size
                dungeon.rooms.append(new_room)
                # add the room rotation
                dungeon.rotation[new_room] = new_rotation
                # add new links
                open_links[new_room] = new_room.links

                if new_connection:
                    # remove connector link of the old room
                    dungeon.connections.append(new_connection)
                    old_room_links = open_links[new_connection[0]]
                    old_room_links.remove(new_connection[1])
                    open_links[new_connection[0]] = old_room_links

                    # remove connector link of the new room
                    new_room_links = open_links[new_room]
                    new_room_links.remove(new_link)
                    open_links[new_room] = new_room_links

                # choose whether to continue
                if size > self.max_size:
                    mutate_loop = False
                elif size > self.min_size:
                    if random.random() > 0.5:
                        mutate_loop = False

                if not open_links.values():
                    mutate_loop = False

        # placement randomization
        self.mutate_placement(dungeon)

    def connect(self, open_links, new_room):
        possible_connections = []
        # check possible connections:
        # for each room, check for all its links with this room's links whether they can connect.
        for old_room in open_links:
            for old_link in open_links[old_room]:
                for new_link in new_room.links:
                    if (old_link[3] % 2 == new_link[3] % 2) and (old_link[4] != new_link[4]):
                        # add this as a possible connection.
                        possible_connections.append([old_room, old_link, new_link])

        if not possible_connections:
            return 0
        else:
            chosen_connection = random.choice(possible_connections)
            return chosen_connection

    def mutate_placement(self, dungeon):
        possible_coordinates = dungeon.get_coordinates().copy()

        dungeon.start = 4
        looking_for_start = True
        while looking_for_start:
            other_starts = []
            random_start = random.choice(possible_coordinates)
            for other in possible_coordinates:
                if uf.is_adjacent(random_start, other):
                    other_starts.append(other)
            if len(other_starts) < 6:
                looking_for_start = False

        certain_starts = random_start

        # while we don't have enough start locations, get more.
        while len(other_starts) + len(certain_starts) < dungeon.start:
            extra_start = random.choice(other_starts)
            other_starts.remove(extra_start)
            certain_starts.append(extra_start)
            for other in possible_coordinates:
                if uf.is_adjacent(extra_start, other) and other not in other_starts and other not in certain_starts:
                    other_starts.append(other)

        all_starts = certain_starts.extend(random.choices(other_starts, k=(dungeon.start - len(certain_starts))))
        dungeon.placement["start"] = all_starts

        # remove the starts from the possible coordinates
        for used_coordinate in all_starts:
            possible_coordinates.remove(used_coordinate)

        # create a "component" dictionary that basically copies the placement dictionary, except for start.
        components = dict()
        monster_count = 0
        for monster_type in dungeon.monsters:
            type_values = dungeon.monsters[monster_type]
            monster_count += type_values[1]
            monster_count += type_values[2]
        components["monsters"] = monster_count
        components["obstacles"] = dungeon.obstacles
        components["traps"] = dungeon.traps
        components["hazardous terrain"] = dungeon.h_terrain
        components["difficult terrain"] = dungeon.d_terrain
        components["chests"] = len(dungeon.chests)
        components["coins"] = dungeon.coins

        for entry in dungeon.placements:
            if entry != "start":
                component_count = components[entry]
                # get a number of random available coordinates equal to the component count
                new_coordinates = random.choices(possible_coordinates, k=component_count)
                dungeon.placements[entry] = new_coordinates

                # remove the coordinates from the available list
                for used_coordinate in new_coordinates:
                    possible_coordinates.remove(used_coordinate)
