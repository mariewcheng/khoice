# Name: merge_lists.py
# Description: This is a python script is used by experiment 5 and 7 in order to
#              read and analyze the SAM file generated by ri-index locate
#              to generate a confusion matrix
#
# Date: June 14th, 2022

import os
import argparse
import math
import csv
import pysam

# Commented out: Cap

def main(args):
    # Set up confusion matrix and reference list
    confusion_matrix = [[0 for i in range(args.num_datasets)] for j in range(args.num_datasets)]

    # Calculate noise from text length file
    if(args.mems):
        with open(args.text, 'r') as fp:
            text_length = fp.readline()
            noise = math.log(int(text_length),4)
        print(f"Noise: {noise}")

    # Go through alignments for each pivot individually - corresponds to 
    # a row in the confusion matrix
    for i in range(args.num_datasets):
        read_mappings = {}
        print("\n[log] building a dictionary of the read alignments for pivot {pivot}".format(pivot = i + 1))
        input_entries = 0
        # Iterates through each alignment for this pivot to populate read mappings
        for j in range(args.num_datasets):
            curr_sam = (pysam.AlignmentFile(args.sam_dir+"pivot_{pivot}_align_dataset_{dataset}.sam".format(pivot = i + 1, dataset = j + 1), "r"))
            for read in curr_sam.fetch():
                query_length = int(read.query_name.split("_")[3])
                # Only uses reads above threshold
                if query_length >= args.t:
                    if args.mems: # MEMs subtract null noise, don't add to map if under noise
                        # Subtract noise
                        if(query_length - noise >= 0):
                            if read.query_name not in read_mappings:
                                read_mappings[read.query_name] = [query_length - noise]
                                input_entries+=len(read.query_sequence) - noise
                            read_mappings[read.query_name].append(j)
                        # Commented out: No noise subtract
                        #if read.query_name not in read_mappings:  
                        #    read_mappings[read.query_name] = [query_length]
                        #    input_entries += query_length
                        #read_mappings[read.query_name].append(j)
                    elif args.half_mems:
                        if read.query_name not in read_mappings:  
                            read_mappings[read.query_name] = [query_length]
                            input_entries+=1
                        read_mappings[read.query_name].append(j)
            curr_sam.close()
        print("Received {num}".format(num=input_entries))
        total_entries = 0
        #ceiling = args.cap
        
        # Populate confusion matrix and count entries
        for key in read_mappings:
            mem_len = read_mappings[key][0]
            curr_set = set(read_mappings[key][1:])
            if args.mems:
                total_entries+=mem_len
            elif args.half_mems:
                total_entries+=1
            for dataset in curr_set:
                if args.mems:
                    confusion_matrix[i][dataset] += 1/len(curr_set) * mem_len
                elif args.half_mems:
                    confusion_matrix[i][dataset] += 1/len(curr_set)
            #if(total_entries >= ceiling):
            #    break
        print("Returned {num}".format(num = total_entries))
        #assert total_entries >= ceiling, "assertion failed: not enough entries to reach cap."
    
    # Create output file
    output_matrix = args.output_dir + "confusion_matrix.csv"
    output_values = args.output_dir + "accuracy_values.csv" 
    
    # Write confusion matrix to output csv
    with open(output_matrix,"w+") as csvfile:
        writer = csv.writer(csvfile)
        for row in confusion_matrix:
            writer.writerow(row)
    
    # Write accuracy values to output csv
    with open(output_values,"w+") as csvfile:
        writer = csv.writer(csvfile)
        for score in calculate_accuracy_values(confusion_matrix,args.num_datasets):
            writer.writerow(score)


def parse_arguments():
    """ Defines the command-line argument parser, and return arguments """
    parser = argparse.ArgumentParser(description="This script helps to analyze the SAM file from experiment 5"
                                                 "in order to form a confusion matrix.")
    parser.add_argument("-n", "--num", dest="num_datasets", required=True, help="number of datasets in this experiment", type=int)
    parser.add_argument("-s", "--sam_file", dest="sam_dir", required=True, help="path to directory with SAM files to be analyzed")
    parser.add_argument("-o", "--output_path", dest = "output_dir", required=True, help="path to directory for output matrix and accuracies")
    #parser.add_argument("-c","--cap", dest = "cap", required=True, help = "number of entries to cap in the confusion matrix", type = int)
    parser.add_argument("--half_mems", action="store_true", default=False, dest="half_mems", help="sam corresponds to half-mems")
    parser.add_argument("--mems", action="store_true", default=False, dest="mems", help="sam corresponds to mems (it can either be mems or half-mems, not both)")

    parser.add_argument("-t", "--threshold", dest = "t", required=False, default=0, help="optional threshold value for experiment 8", type = int)
    parser.add_argument("-l", "--length-text", dest = "text", required=False, default="", help="path to .fai file with total reference length")
    args = parser.parse_args()
    return args

def check_arguments(args):
    """ Checks for invalid arguments """
    if(not os.path.isdir(args.sam_dir)):
        print("Error: sam directory does not exist.")
        exit(1) 
    if(args.num_datasets < 1):
        print("Error: number of datasets must be greater than 0")
    #if(args.cap < 1):
    #    print("Error: number of entries to cap must be greater than 0")
    # Verify only one of the options are chosen: half-mems or mems
    if (args.half_mems and args.mems) or (not args.half_mems and not args.mems):
        print("Error: exactly one type needs to be chosen (--half-mems or --mems)")
        exit(1)
    if(args.half_mems and args.text == ""):
        print("Error: length of text must be specified when using MEMs")
        exit(1)

def calculate_accuracy_values(confusion_matrix, num_datasets):
    """ Calculates accuracy score given confusion matrix """
    accuracies = []
    for pivot in range(num_datasets):
        tp = confusion_matrix[pivot][pivot]
        fp = fn = tn = 0
        for row in range(num_datasets):
            for column in range(num_datasets):
                curr = confusion_matrix[row][column]
                if(column == pivot and row != pivot):
                    fp += curr
                elif(row == pivot and column != pivot):
                    fn += curr
                elif(row != pivot):
                    tn += curr
        accuracies.append([pivot,tp,tn,fp,fn])
    return accuracies


### DEFUNCT AFTER USING M1

#def build_refs_list(ref_lists_dir, num_datasets):
    """ Creates a list of sets containing reference names for each dataset """
    ref_list = []
    for i in range(1,num_datasets + 1):
        curr_file = ref_lists_dir+"dataset_{num}_references.txt".format(num = i)
        curr_set = set()
        with open(curr_file, "r") as input_fd:
            all_lines = [x.strip() for x in input_fd.readlines()]
            for line in all_lines:
                curr_set.add(line)
                curr_set.add("revcomp_"+line)
        ref_list.append(curr_set)
    return ref_list

#def find_class_of_reference_name(ref_list, ref_name):
    """ Finds the class that a particular reference name occurs in """
    datasets = []
    for i, name_set in enumerate(ref_list):
        if ref_name in name_set:
            datasets.append(i+1)
    if len(datasets) != 1:
        print(f"Error: this read hits {len(datasets)} which is not expected.")
        exit(1)
    return datasets[0]


if __name__ == "__main__":
    args = parse_arguments()
    check_arguments(args)
    main(args)