#!/usr/bin/env python3

# PyMaster
# Copyright (C) 2014, 2015 FreedomOfRestriction <FreedomOfRestriction@openmailbox.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__version__ = "0.12"

import sys
import os
import random
import time

import pymasterlib as lib
from pymasterlib.constants import *


def load_text(ID):
    return lib.message.load_text("main", ID)


def main():
    lib.message.init()
    if not os.path.exists(SAVEDIR):
        os.makedirs(SAVEDIR)

    if RESET:
        m = "Are you sure you want to delete your data? This cannot be undone! (You're not trying to weasel your way out of your responsibilities as a slave, are you?)"
        if lib.message.get_bool(m):
            lib.settings.save()
        return

    lib.settings.load()

    if RESET_FACTS:
        lib.slave.facts = {}
        lib.settings.save()
        return

    # This try block is only after the settings are loaded because
    # otherwise, an exception raised before then would cause all of the
    # settings to be overridden with the defaults, which we don't want.
    try:
        if lib.previous_run is None:
            lib.scripts.intro()

        lib.previous_run = STARTUP_TIME

        if lib.slave.bedtime is not None:
            diff = (STARTUP_TIME - lib.slave.bedtime) / ONE_HOUR
            if diff < 6:
                m = load_text("too_early")
                c = [lib.message.load_text("phrases", "assent"),
                     load_text("too_early_request")]
                choice = lib.message.get_choice(m, c, 0)
                if choice == 1:
                    if not lib.slave.sick:
                        lib.slave.add_misdeed("too_early")

                    a = lib.message.load_text("phrases", "thank_you")
                    lib.message.show(load_text("too_early_request_accept"), a)
                    lib.request.what()
                    a = lib.message.load_text("phrases", "assent")
                    lib.message.show(load_text("too_early_now_bed"), a)

                lib.settings.save()
                sys.exit()
            elif diff <= 10:
                lib.message.show(load_text("good_morning"))
                lib.scripts.morning_routine()
            else:
                lib.slave.add_misdeed("too_late")
                lib.message.show(load_text("overslept"))
                lib.scripts.morning_routine()

        def auto_grant():
            if QUICK:
                return False

            for i, activity in sorted(lib.activities,
                                      key=lambda _: random.random()):
                auto_chance = activity.get("auto_chance", 0)
                auto_interval = eval(activity.get("auto_interval", "ONE_HOUR"))
                auto_t = lib.slave.activity_auto_next.get(i, time.time())
                if time.time() >= auto_t:
                    lib.slave.activity_auto_next[i] = (time.time() +
                                                       auto_interval)
                    if not lib.slave.sick and random.random() < auto_chance:
                        if lib.request.request(i):
                            lib.request.allow(i, activity,
                                              load_text("assign_{}".format(i)))
                            return True
            return False

        def assign_routines():
            if QUICK:
                return

            for i in lib.routines_dict:
                if i not in lib.slave.routines:
                    lib.slave.add_routine(i)

            for i in sorted(lib.slave.routines.keys(),
                            key=lambda j: lib.slave.routines[j]):
                if i in lib.routines_dict:
                    if not lib.slave.sick:
                        T = time.time()
                        if T >= lib.slave.routines[i]:
                            lib.assign.routine(i)
                            auto_grant()
                else:
                    print("Warning: Deleting invalid routine \"{}\"".format(i))
                    del lib.slave.routines[i]

            while True:
                if not auto_grant():
                    break

        auto_grant()
        assign_routines()
        choices = [load_text("choice_ask"), load_text("choice_request"),
                   load_text("choice_tell"), load_text("choice_nothing")]
        choice = lib.message.get_choice(load_text("ask_what"), choices,
                                        len(choices) - 1)
        choices[-1] = load_text("choice_done")

        # Main loop
        while choice != len(choices) - 1:
            [lib.ask.what, lib.request.what, lib.tell.what,
             lambda: None][choice]()
            lib.settings.save()
            auto_grant()
            assign_routines()
            choice = lib.message.get_choice(load_text("ask_what_else"),
                                            choices, len(choices) - 1)
    finally:
        # Save the settings when the program is terminated unexpectedly,
        # e.g. if KeyboardInterrupt is raised or if sys.exit is called.
        lib.settings.save()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
