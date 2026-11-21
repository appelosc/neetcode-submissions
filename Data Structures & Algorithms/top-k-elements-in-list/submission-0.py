class Solution:
    def topKFrequent(self, nums: List[int], k: int) -> List[int]:
        count = defaultdict(list)

        for x in nums:
            count[x].append(x)

        return sorted(count, key=lambda n: len(count[n]), reverse=True)[:k]

        