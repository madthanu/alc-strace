import sys
sys.path.append('/home/samer/work/AC/repo/alc-strace/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):

	msg = msg.split('$$$')
	workload_str = msg[0]
	check_str = msg[1]

	if 'dir1_created' in workload_str:
		#if 'ls /|[dir1' not in check_str:
		if '[dir1, zookeeper]' not in check_str and '[dir1, qd, zookeeper]' not in check_str:
			return [FailureCategory.FULL_READ_FAILURE, FailureCategory.FULL_WRITE_FAILURE]
		else:
			if ('set_dir1' in workload_str and 'set_start_dir1' not in workload_str) and 'get /dir1|newv1' not in check_str:
				return [FailureCategory.CORRUPTED_READ_VALUES]
			if 'set_start_dir1' not in workload_str and 'get /dir1|val1' not in check_str:
				return [FailureCategory.CORRUPTED_READ_VALUES]

	if 'dir2_created' in workload_str:
		if 'ls /dir1|[dir2]' not in check_str:
			return [FailureCategory.PARTIAL_READ_FAILURE]
		if 'get /dir1/dir2|val2' not in check_str:
			return [FailureCategory.CORRUPTED_READ_VALUES]

	if 'dir3_created' in workload_str:
		if 'ls /dir1/dir2|[dir3]' not in check_str:
			return [FailureCategory.PARTIAL_READ_FAILURE]
		if 'get /dir1/dir2/dir3|val3' not in check_str:
			return [FailureCategory.CORRUPTED_READ_VALUES]

	if 'file1_created' in workload_str:
		if ('ls /dir1/dir2/dir3|[file2, file1]' not in check_str and 'ls /dir1/dir2/dir3|[file1]' not in check_str):
			return [FailureCategory.PARTIAL_READ_FAILURE]
		elif 'get /dir1/dir2/dir3/file1|valf1' not in check_str:
			return [FailureCategory.CORRUPTED_READ_VALUES]

	if 'file2_created' in workload_str:
		if 'ls /dir1/dir2/dir3|[file2, file1]' not in check_str:
			return [FailureCategory.PARTIAL_READ_FAILURE]
		elif 'get /dir1/dir2/dir3/file2|valf2' not in check_str:
			return [FailureCategory.CORRUPTED_READ_VALUES]

        if 'setquota_dir1' in workload_str and 'listquota /dir1|Output quota for /dir1 count=10,bytes=-1' not in check_str:
                return [FailureCategory.CORRUPTED_READ_VALUES]

        if 'setAcl_dir1' in workload_str and 'getAcl /dir1|\'ip,\'127.0.0.1|: cdrwa' not in check_str:
		return [FailureCategory.CORRUPTED_READ_VALUES]

	if 'qd_again' in workload_str:
		if 'ls /|[dir1, qd, zookeeper]' not in check_str:
			return [FailureCategory.CORRUPTED_READ_VALUES]
		if 'getAcl /qd|\'ip,\'127.0.0.1|: cdrwa' in check_str:
				return [FailureCategory.CORRUPTED_READ_VALUES]
		if 'listquota /qd|Output quota for /dir1 count=10,bytes=-1' in check_str:
				return [FailureCategory.CORRUPTED_READ_VALUES]

	assert(False)



def is_correct(msg):

	#if 'exception' in msg: 
	#	return 'False exception'
		#return False

	msg = msg.split('$$$')
	workload_str = msg[0]
	check_str = msg[1]

	if 'dir1_created' in workload_str:
		#if 'ls /|[dir1' not in check_str:
		if '[dir1, zookeeper]' not in check_str and '[dir1, qd, zookeeper]' not in check_str:
			#return 'False dir1'
			return False
		else:
			if ('set_dir1' in workload_str and 'set_start_dir1' not in workload_str) and 'get /dir1|newv1' not in check_str:
				#return 'False set_dir1'
				return False
			if 'set_start_dir1' not in workload_str and 'get /dir1|val1' not in check_str:
				#return 'False dir1 corrupt'
				return False

	if 'dir2_created' in workload_str:
		if 'ls /dir1|[dir2]' not in check_str:
			#return 'False dir2'
			return False
		if 'get /dir1/dir2|val2' not in check_str:
			#return 'False dir2 corrupt'
			return False

	if 'dir3_created' in workload_str:
		if 'ls /dir1/dir2|[dir3]' not in check_str:
			#return 'False dir3'
			return False
		if 'get /dir1/dir2/dir3|val3' not in check_str:
			#return 'False dir3 corrupt'
			return False

	if 'file1_created' in workload_str:
		if ('ls /dir1/dir2/dir3|[file2, file1]' not in check_str and 'ls /dir1/dir2/dir3|[file1]' not in check_str):
			#return 'False file1'
			return False
		elif 'get /dir1/dir2/dir3/file1|valf1' not in check_str:
			#return 'False file12 corrupt'
			return False

	if 'file2_created' in workload_str:
		if 'ls /dir1/dir2/dir3|[file2, file1]' not in check_str:
			#return 'False file2'
			return False
		elif 'get /dir1/dir2/dir3/file2|valf2' not in check_str:
			#return 'False file2 corrupt'
			return False

        if 'setquota_dir1' in workload_str and 'listquota /dir1|Output quota for /dir1 count=10,bytes=-1' not in check_str:
                #return 'False setquota'
                return False

        if 'setAcl_dir1' in workload_str and 'getAcl /dir1|\'ip,\'127.0.0.1|: cdrwa' not in check_str:
		#return 'False setAcl'
                return False

	if 'qd_again' in workload_str:
		if 'ls /|[dir1, qd, zookeeper]' not in check_str:
			#return 'False qd_again'
			return False
		if 'getAcl /qd|\'ip,\'127.0.0.1|: cdrwa' in check_str:
				#return 'False setAcl_qd_old'
				return False
		if 'listquota /qd|Output quota for /dir1 count=10,bytes=-1' in check_str:
				#return 'False setquota_qd_old'
				return False

	return True


error_reporter.report_errors('???', './strace_description', './replay_output', is_correct, failure_category = failure_category)
#f = open('./replay_output')
#data = f.read()
#for x in data.split('???\n'):
#	if x.strip() == '':
#		continue
#	parts = x.split('###')
#	try:
#		print "0 is " + parts[0] + ":" 
#                print "1 is " + parts[1]
#                print is_correct(parts[1])
#	except:
#		print x
#		raise

