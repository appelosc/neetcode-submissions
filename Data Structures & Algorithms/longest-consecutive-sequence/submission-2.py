class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:

        nums_set = set(nums)
        count = []
        start = False
        for x in nums_set:
            if x -1 not in nums_set:
                seq = 0
                while x in nums_set:
                    x+=1
                    seq = seq+1
                count.append(seq)
        return max(count) if count else 0

                
            
            
        