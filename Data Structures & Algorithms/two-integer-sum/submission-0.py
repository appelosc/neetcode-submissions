class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        hashmap = {}

        for i in range(len(nums)):
            diff = target - nums[i]
            if diff in hashmap:
                return [min(i,hashmap.get(diff)),max(i,hashmap.get(diff))]
            else:
                hashmap[nums[i]] = i

            

        