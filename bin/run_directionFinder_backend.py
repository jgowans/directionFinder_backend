#!/usr/bin/env python

from directionFinder_backend.antenna_array import AntennaArray
from directionFinder_backend.correlator import Correlator
from directionFinder_backend.direction_finder import DirectionFinder
import logging
from colorlog import ColoredFormatter
import time
import argparse
import os

if __name__ == '__main__':
    # setup root logger. Shouldn't be used much but will catch unexpected messages
    colored_formatter = ColoredFormatter("%(log_color)s%(asctime)s:%(levelname)s:%(name)s:%(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(colored_formatter)
    handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    logger = logging.getLogger('main')
    logger.propagate = False
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description = "Run RMS error simulations")
    parser.add_argument('--f_start', default=220e6, type=float)
    parser.add_argument('--f_stop', default=261e6, type=float)
    parser.add_argument('--array_geometry_file', default=None)
    parser.add_argument('--impulse', type=bool, default=False)
    parser.add_argument('--impulse_setpoint', type=int)
    parser.add_argument('--acc_len', type=int, default=40000)
    parser.add_argument('--comment', type=str)
    args = parser.parse_args()

    df_raw_dir = '/home/jgowans/Documents/df_raw/{c}/'.format(c = args.comment)
    if not os.path.exists(df_raw_dir):
        os.mkdir(df_raw_dir)

    array = AntennaArray.mk_from_config(args.array_geometry_file)
    correlator = Correlator(logger = logger.getChild('correlator'))
    correlator.set_accumulation_len(args.acc_len)
    df = DirectionFinder(correlator, array, args.f_start, logger.getChild('df'))

    if args.impulse == True:
        df.set_time()  # go into time mode
        # 100 impulse filter len = 0.5 us
        correlator.set_impulse_filter_len(100)
        correlator.set_impulse_setpoint(args.impulse_setpoint)
        correlator.re_sync()
        time.sleep(0.1)
        correlator.impulse_arm()

    while True:
        if args.impulse == True:
            if df.fetch_impulse() == True:
                correlator.save_time_domain_snapshots(df_raw_dir)
                # not necessary to apply cal as it's done in the correlation routine
                df.df_impulse()
        else:
            df.fetch_frequency_crosses()
            correlator.save_frequency_correlations(df_raw_dir)
            correlator.apply_frequency_domain_calibrations()
            df.df_strongest_signal(args.f_start, args.f_stop)

