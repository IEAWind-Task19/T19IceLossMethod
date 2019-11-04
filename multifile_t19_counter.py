import os
import t19_counter
import collections
import fileinput
import configparser
from multiprocessing import Pool


def find_value_by_tag(filename, option):
    """
    find singular value from a summary file defined by parameter option

    option is exact copy of what reads on the wanted line in the summary file
    """
    not_found = True
    final_value = ''
    with open(filename, 'r') as result_file:
        while not_found:
            try:
                line = next(result_file)
                tokens = line.split('\t')
                tag = tokens[0].strip()
                value = tokens[1].strip()
                if tag == option:
                    not_found = False
                    final_value = value
                    break
            except StopIteration:
                final_value = ''
                break
    return final_value


def parse_summary_file_into_dict(filename):
    """
    reads everyline of the summary file into a dictionary
    """
    done = False
    # results = {}
    results = collections.OrderedDict()
    with open(filename, 'r') as result_file:
        while not done:
            try:
                line = next(result_file)
                tokens = line.split('\t')
                tag = tokens[0].strip()
                value = tokens[1].strip()
                if tag != ' ' or tag != '':
                    results[tag] = value
                else:
                    break
            except StopIteration:
                break
    return results


def clean_results_for_printing(results):
    """
    creates a column for final output file
    """
    output = []
    for k, v in results.items():
        if k != 'Field':
            output.append(v)
    return output


def get_keys_for_printing(results):
    output = []
    for k in results.keys():
        if k != 'Field':
            output.append(k)
    return output


def results_to_file(filename, results, separator='\t'):
    keys = get_keys_for_printing(results[0])
    with open(filename, 'w') as outfile:
        for key in keys:
            line = key
            for summary in results:
                line += separator
                line += summary[key]
            line += '\n'
            outfile.write(line)



def combined_summary(result_directory):
    results = []
    for f in [result_directory + f for f in os.listdir(result_directory) if 'summary.txt' in f]:
        results.append(parse_summary_file_into_dict(f))
    output_filename = os.path.join(result_directory,'_combined_summary.csv')
    results_to_file(output_filename,results)


def main():
    # directory containing all .ini files for individual turbines
    source_directory = './data/siteconfigs/'

    # result_directory, needs to be defined in .ini files as well
    result_directory = './results/'
    
    #get list of .ini files
    
    turbines = [source_directory + filename for filename in os.listdir(source_directory) if ('.ini' in filename) and ('blank') not in filename]
    
    ## run the script sequentially
    # for turb in turbines:
    #     t19_counter.main(turb)
    ## use all 4 cores
    with Pool(4) as p:
        p.map(t19_counter.main,turbines)

    # combine summaryfiles into one large set
    combined_summary(result_directory)
    


if __name__ == '__main__':
    main()
