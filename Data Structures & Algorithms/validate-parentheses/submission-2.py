class Solution:
    def isValid(self, s: str) -> bool:
        matches = {
            "(":")",
            "{":"}",
            "[":"]"
        }
        seen = []

        for x in s:
            if x in matches:
                seen.append(x)
            if x in matches.values():
                if len(seen) == 0:
                    return False
                c = seen.pop()
                if matches.get(c) != x:
                    return False
        return len(seen) == 0