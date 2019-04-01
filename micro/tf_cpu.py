import numpy as np
import pandas as pd
import os
import tensorflow as tf
from tensorflow.python.client import timeline
import sys

# o_orderkey = 0
l_orderkey = 0
l_quantity = 0
l_returnflag = 0
s_nationkey = 0
n_nationkey = 0

def load_input(scale):
    # global o_orderkey
    global l_orderkey
    global l_quantity
    global l_returnflag
    global s_nationkey
    global n_nationkey
    os.chdir('/home/pedroholanda/tpch-' + str(scale))
    # os.chdir('/Users/holanda/Documents/Projects/tpc-tpu/tpch-dbgen')

    lineitem = pd.read_csv("lineitem.tbl", sep='|',
                           names=["l_orderkey", "l_partkey", "l_suppkey", "l_linenumber", "l_quantity",
                                  "l_extendedprice", "l_discount", "l_tax", "l_returnflag", "l_linestatus",
                                  "l_shipdate",
                                  "l_commitdate", "l_receiptdate", "l_shipinstruct", "l_shipmode", "l_comment"],
                           dtype={'l_returnflag': 'category', 'l_linestatus': 'category'})
    # orders = pd.read_csv("orders.tbl", sep='|',
    #                      names=["o_orderkey", "o_custkey", "o_orderstatus", "o_totalprice", "o_orderdate",
    #                             "o_orderpriority", "o_clerk", "o_shippriority", "o_comment"],
    #                      dtype={'o_orderstatus': 'category', 'o_orderpriority': 'category'})

    # o_orderkey = orders["o_orderkey"].values.astype('float32')
    # l_orderkey = lineitem["l_orderkey"].values.astype('int32')

    nation = pd.read_csv("nation.tbl", sep='|', names=["n_nationkey", "n_name", "n_regionkey", "n_comment"])
    supplier = pd.read_csv("supplier.tbl", sep='|',
                           names=["s_suppkey", "s_name", "s_address", "s_nationkey", "s_phone", "s_acctbal", "s_comment"])
    s_suppkey = supplier["s_suppkey"].values.astype('float32')
    s_nationkey = supplier["s_nationkey"].values.astype('float32')
    n_nationkey = nation["n_nationkey"].values.astype('float32')

    l_quantity = lineitem["l_quantity"].values.astype('float32')
    l_returnflag = lineitem["l_returnflag"].values.astype('S1')
    l_returnflag[l_returnflag == "A"] = "1"
    l_returnflag[l_returnflag == "N"] = "2"
    l_returnflag[l_returnflag == "R"] = "3"
    l_returnflag = l_returnflag.astype(np.float32, copy=False)
    os.chdir('/home/pedroholanda/result/')
    # os.chdir('/Users/holanda/Documents/Projects/tpc-tpu/Results')



def filter_sum(scale):
    quantity = tf.placeholder(dtype=tf.float32, shape=(None,), name='quantity')
    zeros = tf.zeros_like(quantity, name='zero')
    result = tf.reduce_sum(
        tf.where(tf.logical_and(tf.greater_equal(quantity, 10, name='GEQ'), tf.less_equal(quantity, 24, name='LEQ'), name='AND'), quantity, zeros, name='FILTER'), name='SUM')
    with tf.Session() as sess:
        run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_metadata = tf.RunMetadata()
        for i in range (0,4):
            res = sess.run(result, feed_dict={
                quantity: l_quantity
            })
        writer = tf.summary.FileWriter("./filter_sum/", sess.graph)
        res = sess.run(result, feed_dict={
            quantity: l_quantity
        }, options=run_options, run_metadata=run_metadata)
        writer.close()
        tl = timeline.Timeline(run_metadata.step_stats)
        ctf = tl.generate_chrome_trace_format()
        with open('timeline_filter_sum_cpu_' + str(scale) + '.json', 'w') as f:
            f.write(ctf)
        print res
    return res


def filter(scale):
    quantity = tf.placeholder(dtype=tf.float32, shape=(None,), name='quantity')
    filter = tf.where(tf.logical_and(tf.greater_equal(quantity, 10, name='GEQ'), tf.less_equal(quantity, 24, name='LEQ'), name='AND'), name='FILTER')
    result = tf.gather(quantity, filter, name='GATHER')
    with tf.Session() as sess:
        run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_metadata = tf.RunMetadata()
        for i in range (0,4):
            res = sess.run(result, feed_dict={
                quantity: l_quantity
            })
        writer = tf.summary.FileWriter("./filter/", sess.graph)
        res = sess.run(result, feed_dict={
            quantity: l_quantity
        }, options=run_options, run_metadata=run_metadata)
        writer.close()
        tl = timeline.Timeline(run_metadata.step_stats)
        ctf = tl.generate_chrome_trace_format()
        with open('timeline_filter_cpu_' + str(scale) + '.json', 'w') as f:
            f.write(ctf)
        print res
    return res


def aggregation(scale):
    quantity = tf.placeholder(dtype=tf.float32, shape=(None,), name='quantity')
    result = tf.reduce_sum(quantity, name='SUM')
    with tf.Session() as sess:
        run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_metadata = tf.RunMetadata()
        for i in range (0,4):
            res = sess.run(result, feed_dict={
                quantity: l_quantity
            })
        writer = tf.summary.FileWriter("./aggregation/", sess.graph)
        res = sess.run(result, feed_dict={
            quantity: l_quantity
        }, options=run_options, run_metadata=run_metadata)
        writer.close()
        tl = timeline.Timeline(run_metadata.step_stats)
        ctf = tl.generate_chrome_trace_format()
        with open('timeline_aggregation_cpu_' + str(scale) + '.json', 'w') as f:
            f.write(ctf)
        print res
    return res


def group_by(scale):
    quantity = tf.placeholder(dtype=tf.float32, shape=(None,), name='quantity')
    returnflag = tf.placeholder(dtype=tf.float32, shape=(None,), name='returnflag')
    ones = tf.ones_like(quantity, name='one')
    zeros = tf.zeros_like(quantity, name='zero')
    returnflag_groups_tensors, idx = tf.unique(returnflag, name='UNIQUE')
    returnflag_groups = tf.unstack(returnflag_groups_tensors, 3, name='UNSTACK')
    result = tf.constant([], dtype=tf.float32, shape=[2], name='result')
    for returnflag_group in returnflag_groups:
        returnflag_filter = tf.cast(tf.where(tf.equal(returnflag, returnflag_group, name='EQUAL'), ones, zeros, name='FILTER'), tf.bool, name='CAST')
        sum_qty = tf.reduce_sum(tf.where(returnflag_filter, quantity, zeros, name='FILTER'), name='SUM')
        result = tf.concat([result, tf.stack([returnflag_group, sum_qty])], axis=0, name='CONCAT')
    result = tf.reshape(result, [4, 2], name='RESHAPE')
    with tf.Session() as sess:
        run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_metadata = tf.RunMetadata()
        for i in range (0,4):
            res = sess.run(result, feed_dict={
                quantity: l_quantity,
                returnflag: l_returnflag
            })
        writer = tf.summary.FileWriter("./group_by/", sess.graph)
        res = sess.run(result, feed_dict={
            quantity: l_quantity,
            returnflag: l_returnflag
        }, options=run_options, run_metadata=run_metadata)
        writer.close()
        tl = timeline.Timeline(run_metadata.step_stats)
        ctf = tl.generate_chrome_trace_format()
        with open('timeline_grouping_cpu_' + str(scale) + '.json', 'w') as f:
            f.write(ctf)
        print res
    return res


def order_by_limit(scale, quantity_size):
    quantity = tf.placeholder(dtype=tf.float32, shape=(None,), name='quantity')
    result = tf.nn.top_k(quantity, quantity_size, True, name='TOP_K')
    with tf.Session() as sess:
        run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_metadata = tf.RunMetadata()
        for i in range (0,4):
            res = sess.run(result, feed_dict={
                quantity: l_quantity
            })
        writer = tf.summary.FileWriter("./order_by_limit/", sess.graph)
        res = sess.run(result, feed_dict={
            quantity: l_quantity
        }, options=run_options, run_metadata=run_metadata)
        writer.close()
        tl = timeline.Timeline(run_metadata.step_stats)
        ctf = tl.generate_chrome_trace_format()
        with open('timeline_order_cpu_' + str(scale) + '.json', 'w') as f:
            f.write(ctf)
        print res
    return res


def join(scale):
    sup_nationkey = tf.placeholder(dtype=tf.float32, shape=(None,))
    nat_nationkey = tf.placeholder(dtype=tf.float32, shape=(None,))

    zeros = tf.zeros_like(sup_nationkey)
    nations = tf.unstack(nat_nationkey, 25) # Number of nations
    index_summation = (tf.constant(1), tf.constant(0.0))
    result = tf.constant([], dtype=tf.int32)

    def condition(index, summation):
        return tf.less(index, 25)

    def body(index, summation):
        nation=tf.gather(nations,index)
        a = tf.equal(sup_nationkey, nation)
        summand = tf.reduce_sum(tf.where(a, sup_nationkey, zeros))

        return tf.add(index, 1), tf.add(summation, summand)
        
    result =  tf.while_loop(condition, body, index_summation,parallel_iterations=25,maximum_iterations=25)[1]
    with tf.Session() as sess:
        run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_metadata = tf.RunMetadata()
        for i in range (0,4):
            res = sess.run(result, feed_dict={
                sup_nationkey: s_nationkey,
                nat_nationkey: n_nationkey
            })
        writer = tf.summary.FileWriter("./join/", sess.graph)
        res = sess.run(result, feed_dict={
                sup_nationkey: s_nationkey,
                nat_nationkey: n_nationkey
        }, options=run_options, run_metadata=run_metadata)
        writer.close()
        tl = timeline.Timeline(run_metadata.step_stats)
        ctf = tl.generate_chrome_trace_format()
        with open('timeline_join_cpu_' + str(scale) + '.json', 'w') as f:
            f.write(ctf)
        print res
    return res


def run_micro(scale):
    load_input(scale)
    filter_sum(scale)
    filter(scale)
    aggregation(scale)
    group_by(scale)
    order_by_limit(scale, 10)
    join(scale)
    return 0


if __name__ == "__main__":
    scale = int(sys.argv[1])
    run_micro(scale)
